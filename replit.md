# Food Exhibition Platform

## Overview

A comprehensive food exhibition platform built with Flask that provides a 3D virtual exhibition experience. The platform connects exhibitors with visitors through interactive galleries, real-time chat, appointment scheduling, and user favorites management. Features multi-role authentication (users, exhibitors, admins), Arabic language support, and real-time communication capabilities.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Template Engine**: Jinja2 with Bootstrap 5 for responsive UI
- **Language Support**: Arabic RTL layout with Cairo font family
- **Styling**: Custom CSS with gradient backgrounds and 3D visual effects
- **JavaScript**: Native JavaScript with Socket.IO for real-time features
- **Calendar Integration**: FullCalendar.js for appointment scheduling

### Backend Architecture
- **Framework**: Flask with SQLAlchemy ORM for database operations
- **Real-time Communication**: Flask-SocketIO for live chat and notifications
- **Authentication**: Replit Auth integration with OAuth2 flow
- **Session Management**: Flask-Login for user session handling
- **Database ORM**: SQLAlchemy with enhanced connection pooling configuration
- **Role-based Access**: Multi-tier user roles (user, exhibitor, admin)

### Database Design
- **User Management**: Users table with role-based permissions
- **Exhibition Structure**: Exhibitors organized by gallery halls (hall1, hall2, hall3)
- **Product Catalog**: Product management with featured items system
- **Social Features**: Favorites system for exhibitors and products
- **Communication**: Chat messages and appointment scheduling
- **Analytics**: User action tracking for exhibitor insights
- **OAuth Storage**: Secure token storage with browser session keys

### Authentication & Authorization
- **OAuth Provider**: Replit Auth with JWT token handling
- **Session Storage**: Custom UserSessionStorage with database persistence
- **Role Management**: Decorator-based access control for different user types
- **Security Features**: Proxy fix middleware for HTTPS URL generation

### Real-time Features
- **Chat System**: Room-based messaging between users and exhibitors
- **Live Updates**: Socket.IO events for real-time notifications
- **User Presence**: Join/leave room tracking for active users

## External Dependencies

### Core Framework Dependencies
- **Flask**: Web framework with SQLAlchemy integration
- **Flask-SocketIO**: WebSocket support for real-time communication
- **Flask-Login**: User session management
- **Flask-Dance**: OAuth2 authentication flow handling

### Database & ORM
- **SQLAlchemy**: Database ORM with connection pooling
- **Database**: PostgreSQL (configured via DATABASE_URL environment variable)
- **Connection Management**: Enhanced stability with pool pre-ping and recycling

### Authentication Service
- **Replit Auth**: OAuth2 provider for user authentication
- **JWT**: Token-based authentication system

### Frontend Libraries
- **Bootstrap 5**: CSS framework for responsive design
- **Font Awesome**: Icon library for UI elements
- **Google Fonts**: Cairo font family for Arabic text support
- **FullCalendar.js**: Calendar widget for appointment scheduling

### Development & Deployment
- **Environment Variables**: SESSION_SECRET and DATABASE_URL configuration
- **Logging**: Built-in Python logging for debugging
- **WSGI**: ProxyFix middleware for production deployment
- **WebSocket Support**: CORS configuration for cross-origin Socket.IO connections