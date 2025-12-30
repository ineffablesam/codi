"""GitHub webhook handlers for build/deploy notifications."""
import hashlib
import hmac
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException, Request

from app.config import settings
from app.database import get_db_context
from app.models.project import Project
from app.utils.logging import get_logger
from app.websocket.connection_manager import connection_manager

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def verify_github_signature(payload: bytes, signature: Optional[str], secret: str) -> bool:
    """Verify GitHub webhook signature.
    
    Args:
        payload: Raw request body
        signature: X-Hub-Signature-256 header value
        secret: Webhook secret
    
    Returns:
        True if signature is valid
    """
    if not signature or not secret:
        return False
    
    expected = "sha256=" + hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected, signature)


@router.post("/github")
async def github_webhook(
    request: Request,
    x_github_event: Optional[str] = Header(None, alias="X-GitHub-Event"),
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
    x_github_delivery: Optional[str] = Header(None, alias="X-GitHub-Delivery"),
) -> Dict[str, Any]:
    """Handle GitHub webhook events.
    
    Handles:
    - workflow_run: Notify frontend when GitHub Actions workflow completes
    - push: Track commits
    - deployment_status: Track deployments
    """
    payload = await request.body()
    
    # Verify signature if secret is configured
    # Note: In production, you should always verify the signature
    webhook_secret = getattr(settings, 'github_webhook_secret', None)
    if webhook_secret:
        if not verify_github_signature(payload, x_hub_signature_256, webhook_secret):
            raise HTTPException(status_code=401, detail="Invalid signature")
    
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    logger.info(f"Received GitHub webhook: {x_github_event}", delivery_id=x_github_delivery)
    
    # Handle workflow_run events (GitHub Actions)
    if x_github_event == "workflow_run":
        await handle_workflow_run(data)
    
    # Handle deployment_status events
    elif x_github_event == "deployment_status":
        await handle_deployment_status(data)
    
    # Handle push events
    elif x_github_event == "push":
        await handle_push(data)
    
    return {"status": "ok", "event": x_github_event}


async def handle_workflow_run(data: Dict[str, Any]) -> None:
    """Handle workflow_run webhook event.
    
    Notifies frontend when a GitHub Actions workflow starts or completes.
    """
    workflow_run = data.get("workflow_run", {})
    action = data.get("action", "")
    repo_full_name = data.get("repository", {}).get("full_name", "")
    workflow_name = workflow_run.get("name", "")
    html_url = workflow_run.get("html_url", "")
    
    # Find the project by repo name
    async with get_db_context() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(Project).where(Project.github_repo_full_name == repo_full_name)
        )
        project = result.scalar_one_or_none()
    
    if not project:
        logger.warning(f"No project found for repo: {repo_full_name}")
        return
    
    # Handle in_progress -> notify frontend that build is running
    if action == "in_progress":
        logger.info(f"Workflow in progress: {workflow_name}", repo=repo_full_name)
        await connection_manager.send_build_progress(
            project_id=project.id,
            stage="building",
            message="🔨 Build in progress...",
            progress=0.3,
        )
        return
    
    # Handle requested (workflow just started)
    if action == "requested":
        logger.info(f"Workflow requested: {workflow_name}", repo=repo_full_name)
        await connection_manager.send_build_progress(
            project_id=project.id,
            stage="queued",
            message="📋 Build queued...",
            progress=0.1,
        )
        return
    
    # Only process completed workflows further
    if action != "completed":
        return
    
    conclusion = workflow_run.get("conclusion", "")  # success, failure, cancelled, etc.
    
    logger.info(
        f"Workflow completed: {workflow_name}",
        repo=repo_full_name,
        conclusion=conclusion,
    )
    
    # Update project in database
    async with get_db_context() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(Project).where(Project.github_repo_full_name == repo_full_name)
        )
        project = result.scalar_one_or_none()
        if project:
            project.last_build_status = conclusion
            project.last_build_at = datetime.utcnow()
            await session.commit()
    
    # Determine deployment URL with cache-busting parameter
    deployment_url = None
    if project.deployment_url:
        # Add cache-busting parameter
        timestamp = int(datetime.utcnow().timestamp())
        separator = "&" if "?" in project.deployment_url else "?"
        deployment_url = f"{project.deployment_url}{separator}v={timestamp}"
    
    # Send WebSocket notification
    if conclusion == "success":
        await connection_manager.send_deployment_complete(
            project_id=project.id,
            status="success",
            message=f"✅ Build completed successfully!",
            deployment_url=deployment_url,
            build_time=workflow_run.get("run_started_at"),
        )
        
        # Also send agent status to update UI
        await connection_manager.send_agent_status(
            project_id=project.id,
            agent="build_deploy",
            status="completed",
            message="Build completed - preview ready",
            details={
                "workflow_name": workflow_name,
                "conclusion": conclusion,
                "workflow_url": html_url,
                "deployment_url": deployment_url,
            },
        )
    else:
        await connection_manager.send_error(
            project_id=project.id,
            agent="build_deploy",
            error=f"Build {conclusion}",
            message=f"❌ Build {conclusion}. Check GitHub Actions for details.",
            details={
                "workflow_name": workflow_name,
                "workflow_url": html_url,
            },
        )


async def handle_deployment_status(data: Dict[str, Any]) -> None:
    """Handle deployment_status webhook event."""
    deployment = data.get("deployment", {})
    deployment_status = data.get("deployment_status", {})
    
    state = deployment_status.get("state", "")  # pending, success, failure, error
    environment_url = deployment_status.get("environment_url", "")
    
    repo_full_name = data.get("repository", {}).get("full_name", "")
    
    # Find the project
    async with get_db_context() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(Project).where(Project.github_repo_full_name == repo_full_name)
        )
        project = result.scalar_one_or_none()
        
        if not project:
            return
        
        if state == "success" and environment_url:
            # Update deployment_url in DB if different from calculated
            if environment_url and environment_url != project.deployment_url:
                logger.info(f"Updating deployment_url from {project.deployment_url} to {environment_url}")
                project.deployment_url = environment_url
            
            project.last_deployment_at = datetime.utcnow()
            await session.commit()
            
            # Add cache-busting parameter for WebSocket notification
            timestamp = int(datetime.utcnow().timestamp())
            separator = "&" if "?" in environment_url else "?"
            deployment_url_with_cache_bust = f"{environment_url}{separator}v={timestamp}"
            
            await connection_manager.send_deployment_complete(
                project_id=project.id,
                status="success",
                message="🚀 Deployed successfully!",
                deployment_url=deployment_url_with_cache_bust,
            )


async def handle_push(data: Dict[str, Any]) -> None:
    """Handle push webhook event."""
    repo_full_name = data.get("repository", {}).get("full_name", "")
    commits = data.get("commits", [])
    ref = data.get("ref", "")
    
    # Find the project
    async with get_db_context() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(Project).where(Project.github_repo_full_name == repo_full_name)
        )
        project = result.scalar_one_or_none()
    
    if not project:
        return
    
    # Notify about push
    if commits:
        latest_commit = commits[-1]
        await connection_manager.send_git_operation(
            project_id=project.id,
            operation="push",
            message=f"Push: {latest_commit.get('message', '')[:50]}",
            commit_sha=latest_commit.get("id", "")[:7],
            branch_name=ref.replace("refs/heads/", ""),
            files_changed=len(latest_commit.get("added", []) + latest_commit.get("modified", []) + latest_commit.get("removed", [])),
        )
