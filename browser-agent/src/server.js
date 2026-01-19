/**
 * Codi Browser Agent Service
 * 
 * Provides REST API + WebSocket for browser automation using agent-browser.
 * Used by Python BrowserAgent for AI-driven browser control.
 */

import express from 'express';
import cors from 'cors';
import { WebSocketServer } from 'ws';
import { createServer } from 'http';
import { v4 as uuidv4 } from 'uuid';
import { BrowserManager } from 'agent-browser/dist/browser.js';
import { executeCommand } from 'agent-browser/dist/actions.js';

const app = express();
app.use(cors());
app.use(express.json());

// Session storage: sessionId -> { browser, page, createdAt, currentUrl, lastFrame, screencastActive }
const sessions = new Map();

// Stream WebSocket connections: sessionId -> Set<WebSocket>
const streamConnections = new Map();

const PORT = process.env.PORT || 3001;

// ============================================================================
// REST API Endpoints
// ============================================================================

// Health check
app.get('/health', (req, res) => {
    res.json({
        status: 'ok',
        sessions: sessions.size,
        uptime: process.uptime(),
    });
});

// Create browser session
app.post('/session', async (req, res) => {
    try {
        const { initial_url = 'https://google.com', viewport } = req.body;
        const sessionId = uuidv4().slice(0, 8);

        console.log(`Creating session ${sessionId} with initial URL: ${initial_url}`);

        const browser = new BrowserManager();
        await browser.launch({
            headless: true,
            args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        });

        // Get the page instance
        const page = await browser.getPage();

        if (viewport) {
            await page.setViewportSize({ width: viewport.width, height: viewport.height });
        } else {
            // Default to Desktop 1280x800 (16:10) to match frontend defaults
            await page.setViewportSize({ width: 800, height: 1280 });
        }

        if (req.body.userAgent) {
            await page.setExtraHTTPHeaders({
                'User-Agent': req.body.userAgent
            });
        }

        const session = {
            browser,
            page,
            createdAt: Date.now(),
            currentUrl: initial_url,
            lastFrame: null,
            screencastActive: false,
        };

        sessions.set(sessionId, session);

        // Setup screencast using CDP directly via Playwright
        try {
            const client = await page.context().newCDPSession(page);

            await client.send('Page.startScreencast', {
                format: 'jpeg',
                quality: 60,
                maxWidth: 1280,
                maxHeight: 800,
                everyNthFrame: 1,
            });

            client.on('Page.screencastFrame', async (event) => {
                session.lastFrame = event.data;

                // Acknowledge the frame
                await client.send('Page.screencastFrameAck', { sessionId: event.sessionId });

                // Forward to all connected WebSockets for this session
                const connections = streamConnections.get(sessionId);
                if (connections && connections.size > 0) {
                    const message = JSON.stringify({
                        type: 'browser_frame',
                        image: event.data,
                        format: 'jpeg',
                        timestamp: Date.now(),
                        metadata: event.metadata
                    });

                    // Log first frame to confirm it's working
                    if (!session.hasLoggedFirstFrame) {
                        console.log(`Sending first screencast frame for session ${sessionId}`);
                        session.hasLoggedFirstFrame = true;
                    }

                    for (const ws of connections) {
                        if (ws.readyState === 1) {
                            ws.send(message);
                        }
                    }
                }
            });

            session.cdpSession = client;
            session.screencastActive = true;
            session.hasLoggedFirstFrame = false;
            console.log(`Screencast started for session ${sessionId}`);
        } catch (err) {
            console.error(`Failed to start screencast for ${sessionId}:`, err);
        }

        // Navigate to initial URL
        await page.goto(initial_url, { waitUntil: 'domcontentloaded' });
        session.currentUrl = initial_url;

        console.log(`Session ${sessionId} created and screencast started`);

        res.json({
            session_id: sessionId,
            url: initial_url,
        });
    } catch (error) {
        console.error('Failed to create session:', error);
        res.status(500).json({ error: error.message });
    }
});

// Get session info
app.get('/session/:id', (req, res) => {
    const session = sessions.get(req.params.id);
    if (!session) {
        return res.status(404).json({ error: 'Session not found' });
    }
    res.json({
        session_id: req.params.id,
        currentUrl: session.currentUrl,
        createdAt: session.createdAt,
        age_ms: Date.now() - session.createdAt,
    });
});

// Get screenshot (for AI vision)
app.get('/session/:id/screenshot', async (req, res) => {
    const sessionId = req.params.id;
    const session = sessions.get(sessionId);
    if (!session) {
        return res.status(404).json({ error: 'Session not found' });
    }

    try {
        // If we have a recent frame from screencast, use it
        if (session.lastFrame) {
            return res.json({ image: session.lastFrame, format: 'jpeg' });
        }

        // Fallback to manual screenshot via Playwright page
        const screenshot = await session.page.screenshot({
            type: 'png',
            encoding: 'base64'
        });
        res.json({ image: screenshot, format: 'png' });
    } catch (error) {
        console.error(`Screenshot failed for ${sessionId}:`, error);
        res.status(500).json({ error: error.message });
    }
});

// Get accessibility snapshot (for AI element refs)
app.get('/session/:id/snapshot', async (req, res) => {
    const sessionId = req.params.id;
    const session = sessions.get(sessionId);
    if (!session) {
        return res.status(404).json({ error: 'Session not found' });
    }

    try {
        // Support interactive_only filter from query params
        const interactiveOnly = req.query.interactive === 'true' || req.query.interactive_only === 'true';

        // Use executeCommand to get snapshot, just like the CLI does
        const result = await executeCommand({
            id: uuidv4(),
            action: 'snapshot',
            interactive: interactiveOnly
        }, session.browser);

        res.json(result);
    } catch (error) {
        console.error(`Snapshot failed for ${sessionId}:`, error);
        res.status(500).json({ error: error.message });
    }
});

// Get current URL
app.get('/session/:id/url', async (req, res) => {
    const sessionId = req.params.id;
    const session = sessions.get(sessionId);
    if (!session) {
        return res.status(404).json({ error: 'Session not found' });
    }

    try {
        const url = session.page.url();
        res.json({ url });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Execute browser command - UPGRADED with all agent-browser commands
app.post('/session/:id/command', async (req, res) => {
    const sessionId = req.params.id;
    const session = sessions.get(sessionId);
    if (!session) {
        return res.status(404).json({ error: 'Session not found' });
    }

    const { command, args = {} } = req.body;
    const { browser, page } = session;
    console.log(`[${sessionId}] Command: ${command}`, args);

    try {
        let result;

        // Map of commands and how to execute them
        // Commands supported natively by executeCommand from agent-browser
        const executeCommandActions = [
            'navigate', 'open', 'goto',
            'click', 'dblclick',
            'fill', 'type',
            'press', 'keydown', 'keyup',
            'scroll', 'scrollintoview', 'scrollinto',
            'wait',
            'hover',
            'focus',
            'select',
            'check', 'uncheck',
            'drag',
            'upload',
            'screenshot',
            'eval',
            'back', 'forward', 'reload',
            'snapshot'
        ];

        // Get commands (agent-browser native)
        const getCommands = [
            'get_text', 'get_html', 'get_value', 'get_attr',
            'get_title', 'get_url', 'get_count', 'get_box'
        ];

        // Check/Is commands (agent-browser native)
        const checkCommands = [
            'is_visible', 'is_enabled', 'is_checked'
        ];

        // Normalize command name for agent-browser
        let action = command;

        // Handle Python snake_case to agent-browser naming
        if (command === 'get_text') action = 'get text';
        else if (command === 'get_html') action = 'get html';
        else if (command === 'get_value') action = 'get value';
        else if (command === 'get_attr') action = 'get attr';
        else if (command === 'get_title') action = 'get title';
        else if (command === 'get_url') action = 'get url';
        else if (command === 'get_count') action = 'get count';
        else if (command === 'get_box') action = 'get box';
        else if (command === 'is_visible') action = 'is visible';
        else if (command === 'is_enabled') action = 'is enabled';
        else if (command === 'is_checked') action = 'is checked';
        else if (command === 'scrollintoview') action = 'scrollintoview';

        // Build command object for executeCommand
        const cmdObj = {
            id: uuidv4(),
            action: action,
            ...args
        };

        // Execute the command using agent-browser's executeCommand
        result = await executeCommand(cmdObj, browser);

        // Update current URL if navigation occurred
        if (['navigate', 'open', 'goto'].includes(command)) {
            session.currentUrl = args.url || session.page.url();
        }

        res.json({ success: true, result });
    } catch (error) {
        console.error(`Command ${command} failed for ${sessionId}:`, error);
        res.status(500).json({ error: error.message });
    }
});

// Close session
app.delete('/session/:id', async (req, res) => {
    const sessionId = req.params.id;
    const session = sessions.get(sessionId);

    if (session) {
        try {
            // Stop screencast if active
            if (session.screencastActive && session.cdpSession) {
                try {
                    await session.cdpSession.send('Page.stopScreencast');
                    await session.cdpSession.detach();
                } catch (err) {
                    console.warn(`Could not stop screencast for ${sessionId}:`, err.message);
                }
            }

            // Close browser
            await session.browser.close();
        } catch (error) {
            console.warn(`Error closing session ${sessionId}:`, error.message);
        }
        sessions.delete(sessionId);

        // Close any stream connections
        const connections = streamConnections.get(sessionId);
        if (connections) {
            connections.forEach(ws => ws.close());
            streamConnections.delete(sessionId);
        }
    }

    console.log(`Session ${sessionId} closed`);
    res.json({ success: true });
});

// ============================================================================
// WebSocket for Live Streaming
// ============================================================================

const server = createServer(app);
const wss = new WebSocketServer({ server, path: '/stream' });

wss.on('connection', (ws, req) => {
    const url = new URL(req.url, `http://${req.headers.host}`);
    const sessionId = url.searchParams.get('session');

    if (!sessionId || !sessions.get(sessionId)) {
        ws.close(1008, 'Invalid session');
        return;
    }

    console.log(`Stream connection opened for session ${sessionId}`);

    if (!streamConnections.has(sessionId)) {
        streamConnections.set(sessionId, new Set());
    }
    streamConnections.get(sessionId).add(ws);

    // If we have a last frame, send it immediately
    const session = sessions.get(sessionId);
    if (session && session.lastFrame) {
        ws.send(JSON.stringify({
            type: 'browser_frame',
            image: session.lastFrame,
            timestamp: Date.now(),
        }));
    }

    ws.on('message', async (data) => {
        try {
            const event = JSON.parse(data.toString());
            const session = sessions.get(sessionId);
            if (!session || !session.cdpSession) return;

            if (event.type === 'input_mouse') {
                await session.cdpSession.send('Input.dispatchMouseEvent', {
                    type: event.eventType,
                    x: event.x,
                    y: event.y,
                    button: event.button || 'left',
                    clickCount: event.clickCount || 1
                });
            } else if (event.type === 'input_keyboard') {
                await session.cdpSession.send('Input.dispatchKeyEvent', {
                    type: event.eventType,
                    key: event.key,
                    code: event.code || event.key
                });
            } else if (event.type === 'set_viewport') {
                console.log(`Setting viewport for session ${sessionId}: ${event.width}x${event.height}, Mobile: ${event.isMobile}`);
                await session.page.setViewportSize({ width: event.width, height: event.height });

                // User Agent update
                if (event.userAgent) {
                    await session.page.setExtraHTTPHeaders({
                        'User-Agent': event.userAgent
                    });
                } else {
                    const desktopUA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36';
                    await session.page.setExtraHTTPHeaders({
                        'User-Agent': desktopUA
                    });
                }

                // Restart screencast to match new viewport dimensions dynamically
                if (session.cdpSession) {
                    try {
                        await session.cdpSession.send('Page.stopScreencast');
                        await session.cdpSession.send('Page.startScreencast', {
                            format: 'jpeg',
                            quality: 60,
                            maxWidth: event.width,
                            maxHeight: event.height,
                            everyNthFrame: 1,
                        });
                        console.log(`Restarted screencast for ${sessionId} with size ${event.width}x${event.height}`);
                    } catch (err) {
                        console.warn(`Failed to update screencast size: ${err.message}`);
                    }
                }
            }
        } catch (error) {
            console.warn('Failed to process input event:', error.message);
        }
    });

    ws.on('close', () => {
        streamConnections.get(sessionId)?.delete(ws);
        console.log(`Stream connection closed for session ${sessionId}`);
    });
});

// ============================================================================
// Start Server
// ============================================================================

server.listen(PORT, '0.0.0.0', () => {
    console.log(`🌐 Browser Agent Service running on port ${PORT}`);
    console.log(`   REST API: http://localhost:${PORT}`);
    console.log(`   WebSocket: ws://localhost:${PORT}/stream`);
    console.log(`   Supported commands: navigate, click, fill, type, press, scroll, hover, snapshot, get_*, is_*, and more`);
});

// Graceful shutdown
process.on('SIGTERM', async () => {
    console.log('Shutting down...');
    for (const [sessionId, session] of sessions) {
        try {
            if (session.cdpSession) {
                await session.cdpSession.detach().catch(() => { });
            }
            await session.browser.close();
        } catch { }
    }
    server.close(() => process.exit(0));
});