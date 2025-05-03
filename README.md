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

## License
[Your License Here] 