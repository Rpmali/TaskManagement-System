# Task Management System

A modern task management system built with FastAPI and Firebase, featuring real-time collaboration and authentication.

## Technologies Used

### Backend
- **FastAPI**: Modern, fast web framework for building APIs with Python
- **Python**: Primary programming language
- **Firebase**: 
  - **Firebase Authentication**: User authentication and management
  - **Firestore**: NoSQL database for storing user data, boards, and tasks
  - **Google Cloud Platform**: Hosting and infrastructure

### Authentication
- **Google Firebase Authentication**: Secure user authentication system
- **JWT (JSON Web Tokens)**: Token-based authentication
- **OAuth 2.0**: Secure authorization framework

### Database
- **Firestore**: 
  - Real-time NoSQL database
  - Document-based data structure
  - Automatic scaling and high availability

### API Features
- RESTful API endpoints
- Real-time data synchronization
- CRUD operations for:
  - Users
  - Boards
  - Tasks
  - Board Members

### Security
- Token-based authentication
- Role-based access control
- Secure API endpoints
- Data validation and sanitization

## Project Structure
- `main.py`: Core application logic and API endpoints
- `templates/`: HTML templates for the web interface
- `static/`: Static assets (CSS, JavaScript, images)

## Key Features
- User authentication and authorization
- Board creation and management
- Task creation, assignment, and tracking
- Real-time collaboration
- Role-based permissions
- Task status tracking
- Due date management
- Member management

## Getting Started
1. Clone the repository
2. Set up Firebase project and configure credentials
3. Install dependencies
4. Run the application

## Dependencies
- fastapi
- google-cloud-firestore
- google-auth
- python-jose
- uvicorn
- jinja2
- starlette

## Prerequisites

Before running this project, you'll need:

1. Node.js installed on your system
2. A Google Cloud Platform account
3. A Firebase project
4. Git installed on your system

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/Rpmali/TaskManagement-System.git
cd TaskManagement-System
```

### 2. Firebase Setup

1. Go to the [Firebase Console](https://console.firebase.google.com/)
2. Create a new project or select an existing one
3. Enable Authentication with Email/Password provider
4. Download your service account key:
   - Go to Project Settings > Service Accounts
   - Click "Generate New Private Key"
   - Save the downloaded JSON file as `your-private-key.json` in your project root

### 3. Configure Firebase

1. Open `static/firebase-login.js`
2. Replace the Firebase configuration with your own:

```javascript
const firebaseConfig = {
  apiKey: "your-api-key",
  authDomain: "your-auth-domain",
  projectId: "your-project-id",
  storageBucket: "your-storage-bucket",
  messagingSenderId: "your-messaging-sender-id",
  appId: "your-app-id"
};
```

You can find these values in your Firebase project settings under "General" > "Your apps" > "Web app".

### 4. Install Dependencies

```bash
npm install
```

### 5. Run the Application

```bash
npm start
```

The application will be available at `http://localhost:3000`

## Project Structure

- `static/` - Contains static files including JavaScript and CSS
  - `firebase-login.js` - Handles Firebase authentication
- `your-private-key.json` - Google Cloud service account credentials
- `app.js` - Main application file
- `package.json` - Project dependencies and scripts

## Features

- User Authentication (Sign up, Login, Logout)
- Task Management
- Real-time updates
- Secure data storage

## Security Notes

- Never commit your `your-private-key.json` file to version control
- Keep your Firebase configuration secure
- Use environment variables for sensitive information

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request 
