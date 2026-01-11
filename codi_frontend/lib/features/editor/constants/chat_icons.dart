import 'package:fluentui_system_icons/fluentui_system_icons.dart';
import 'package:heroicons/heroicons.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:solar_icon_pack/solar_icon_pack.dart';

class StatusIcons {
  // Thinking/Planning
  static const thinking = LucideIcons.brain;
  static const planning = LucideIcons.lightbulb;
  static const analyzing = LucideIcons.search;

  // Working/Progress
  static const building = LucideIcons.hammer;
  static const generating = LucideIcons.sparkles;
  static const processing = LucideIcons.loader;

  // Success/Completion
  static const success = LucideIcons.circleCheck;
  static const completed = LucideIcons.check;
  static const deployed = LucideIcons.rocket;

  // Error/Warning
  static const error = LucideIcons.circleX;
  static const warning = LucideIcons.triangleAlert;
  static const info = LucideIcons.info;

  // File Operations
  static const fileCreate = LucideIcons.filePlus;
  static const fileUpdate = LucideIcons.filePen;
  static const fileDelete = LucideIcons.fileX;
  static const fileRead = LucideIcons.fileText;
  static const folder = LucideIcons.folder;
  static const file = LucideIcons.file;

  // Git Operations
  static const gitBranch = LucideIcons.gitBranch;
  static const gitCommit = LucideIcons.gitCommitHorizontal;
  static const gitPush = LucideIcons.upload;
  static const gitMerge = LucideIcons.gitMerge;
  static const gitPull = LucideIcons.download;

  // Code/Development
  static const code = LucideIcons.code;
  static const terminal = LucideIcons.terminal;
  static const package = LucideIcons.package;
  static const bug = LucideIcons.bug;
  static const review = LucideIcons.eye;

  // Build/Deploy
  static const build = LucideIcons.settings;
  static const deploy = LucideIcons.cloud;
  static const server = LucideIcons.server;
  static const database = LucideIcons.database;

  // Communication
  static const message = LucideIcons.messageCircle;
  static const chat = LucideIcons.messageSquare;
  static const send = LucideIcons.send;
  static const user = LucideIcons.user;

  // Navigation
  static const link = LucideIcons.link;
  static const externalLink = LucideIcons.externalLink;
  static const download = LucideIcons.download;
  static const refresh = LucideIcons.refreshCw;

  // Time/Duration
  static const clock = LucideIcons.clock;
  static const timer = LucideIcons.timer;
  static const history = LucideIcons.history;

  // Quality/Testing
  static const testTube = LucideIcons.flaskConical;
  static const shield = LucideIcons.shield;
  static const checkSquare = LucideIcons.squareCheck;

  // Misc
  static const activity = LucideIcons.activity;
  static const plus = LucideIcons.plus;
  static const palette = LucideIcons.palette;
}

class AgentAvatarIcons {
  // Main agent types (use these instead of emojis)
  static const planner = FluentIcons.brain_circuit_20_regular;
  static const coder = FluentIcons.code_20_regular;
  static const reviewer = FluentIcons.eye_tracking_20_regular;
  static const gitOperator = FluentIcons.branch_20_regular;
  static const buildDeploy = FluentIcons.rocket_20_regular;
  static const memory = FluentIcons.database_20_regular;
  static const ai = FluentIcons.bot_20_regular;
}

class ActionIcons {
  // User actions
  static const play = HeroIcons.play;
  static const pause = HeroIcons.pause;
  static const stop = HeroIcons.stop;
  static const retry = HeroIcons.arrowPath;

  // Document actions
  static const view = HeroIcons.eye;
  static const edit = HeroIcons.pencil;
  static const copy = HeroIcons.documentDuplicate;
  static const delete = HeroIcons.trash;

  // Settings
  static const settings = HeroIcons.cog6Tooth;
  static const filter = HeroIcons.funnel;
  static const sort = HeroIcons.barsArrowDown;
}

class ProgressIcons {
  // Progress states
  static const pending = SolarLinearIcons.clockCircle;
  static const inProgress = SolarLinearIcons.refresh;
  static const completed = SolarLinearIcons.checkCircle;
  static const failed = SolarLinearIcons.closeCircle;

  // Deployment
  static const deploying = SolarLinearIcons.cloudUpload;
  static const deployed = SolarLinearIcons.cloudCheck;
  static const cloudError = SolarLinearIcons.cloudMinus;
}
