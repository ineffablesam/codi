/// Application string constants
library;

/// Application strings (can be extended for localization)
class AppStrings {
  AppStrings._();

  // App name
  static const String appName = 'Codi';
  static const String appTagline = 'AI-powered Flutter development';

  // Auth
  static const String loginWithGitHub = 'Sign in with Github';
  static const String loginWithGoogle = 'Continue with Google';
  static const String loginTitle = 'Welcome to Codi';
  static const String loginSubtitle = 'Build Flutter apps with AI assistance';
  static const String loggingIn = 'Signing you in...';
  static const String logout = 'Log out';
  static const String logoutConfirm = 'Are you sure you want to log out?';

  // Projects
  static const String myProjects = 'My Projects';
  static const String newProject = 'New Project';
  static const String createProject = 'Create Project';
  static const String projectName = 'Project Name';
  static const String projectDescription = 'Description (optional)';
  static const String projectNameHint = 'my-awesome-app';
  static const String projectDescriptionHint = 'A description for your project';
  static const String privateProject = 'Private repository';
  static const String creating = 'Creating...';
  static const String noProjects = 'No projects yet';
  static const String noProjectsSubtitle =
      'Create your first project to get started';
  static const String deleteProject = 'Delete Project';
  static const String deleteConfirm =
      'Are you sure you want to delete this project?';

  // Editor
  static const String editor = 'Editor';
  static const String preview = 'Preview';
  static const String chat = 'Chat';
  static const String agentActivity = 'Agent Activity';
  static const String typeMessage = 'Type your message...';
  static const String send = 'Send';
  static const String noPreview = 'No preview yet';
  static const String noPreviewSubtitle = 'Build your project to see preview';
  static const String loadingPreview = 'Loading preview...';
  static const String refresh = 'Refresh';
  static const String openInBrowser = 'Open in browser';
  static const String startConversation = 'Start a conversation';
  static const String startConversationSubtitle =
      'Ask me to build features for your app';
  static const String working = 'Working...';

  // Agents
  static const String planner = 'Planner';
  static const String flutterEngineer = 'Flutter Engineer';
  static const String codeReviewer = 'Code Reviewer';
  static const String gitOperator = 'Git Operator';
  static const String buildDeploy = 'Build & Deploy';
  static const String memory = 'Memory';

  // Status messages
  static const String started = 'Started';
  static const String inProgress = 'In progress';
  static const String completed = 'Completed';
  static const String failed = 'Failed';

  // File operations
  static const String created = 'CREATED';
  static const String updated = 'UPDATED';
  static const String deleted = 'DELETED';

  // Git operations
  static const String createdBranch = 'CREATED BRANCH';
  static const String committed = 'COMMITTED';
  static const String pushed = 'PUSHED';
  static const String merged = 'MERGED';

  // Build & Deploy
  static const String building = 'Building...';
  static const String deploying = 'Deploying...';
  static const String deployedSuccessfully = 'Deployed successfully!';
  static const String buildFailed = 'Build failed';
  static const String deploymentFailed = 'Deployment failed';

  // Deployments
  static const String deployments = 'Deployments';
  static const String noDeployments = 'No deployments yet';
  static const String noDeploymentsSubtitle =
      'Deploy your project to see history';
  static const String viewDeployment = 'View Deployment';

  // Settings
  static const String settings = 'Settings';
  static const String account = 'Account';
  static const String appearance = 'Appearance';
  static const String darkMode = 'Dark Mode';
  static const String notifications = 'Notifications';
  static const String about = 'About';
  static const String version = 'Version';
  static const String privacyPolicy = 'Privacy Policy';
  static const String termsOfService = 'Terms of Service';

  // Errors
  static const String error = 'Error';
  static const String connectionError = 'Connection error';
  static const String connectionErrorMessage =
      'Unable to connect to server. Please try again.';
  static const String somethingWentWrong = 'Something went wrong';
  static const String tryAgain = 'Try again';
  static const String cancel = 'Cancel';
  static const String ok = 'OK';
  static const String yes = 'Yes';
  static const String no = 'No';

  // WebSocket
  static const String connected = 'Connected';
  static const String disconnected = 'Disconnected';
  static const String reconnecting = 'Reconnecting...';
  static const String realTimeUpdatesEnabled = 'Real-time updates enabled';
}
