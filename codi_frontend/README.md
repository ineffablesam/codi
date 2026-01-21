# Codi Frontend

AI-powered Flutter development platform mobile app.

## Features

- GitHub OAuth authentication
- Real-time agent chat with 10+ message types
- Embedded WebView preview panel
- Project management
- Build and deployment tracking

## Getting Started

1. Install dependencies:
```bash
flutter pub get
```

2. Configure environment:
- Copy `.env.example` to `.env`
- Set API URL and other configuration

3. Run the app:
```bash
flutter run
```

## Architecture

- **State Management**: GetX
- **HTTP Client**: Dio with interceptors
- **WebSocket**: Real-time agent updates
- **Storage**: shared_preferences

## Project Structure

```
lib/
├── main.dart
├── app.dart
├── config/
│   ├── env.dart
│   ├── theme.dart
│   └── routes.dart
├── core/
│   ├── api/
│   ├── constants/
│   ├── storage/
│   └── utils/
├── features/
│   ├── auth/
│   ├── projects/
│   ├── editor/
│   ├── deployments/
│   └── settings/
├── shared/
│   └── widgets/
└── bindings/
```

##Testings

church-website
A Church Website for Hoboken Grace with light and sophisticated user interface with donations, events, sermons, and blog pages.








