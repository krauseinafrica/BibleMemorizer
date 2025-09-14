# Bible Verse Memorization Tool

A comprehensive web application for Bible verse memorization with advanced student tracking, reporting, and class management capabilities.

## Features

### For Students
- Interactive verse memorization with speech recognition
- Real-time scoring using fuzzy text matching
- Progress tracking and personal dashboards
- Visual feedback with error highlighting
- Mobile-friendly responsive design

### For Teachers/Administrators
- Class management and student organization
- Comprehensive progress reporting and analytics
- Custom verse set creation and assignment
- Detailed error pattern analysis
- Data export capabilities (CSV, reports)
- Individual student performance tracking

### Technical Features
- SQLite database with comprehensive schema
- RESTful API architecture
- User authentication and session management
- Anonymous user support for quick access
- Advanced text comparison algorithms
- Error analysis and pattern recognition

## Quick Start

### Prerequisites
- Python 3.8+
- pip (Python package installer)

### Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd /var/www/BibleMemorizer
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment:**
   ```bash
   cp .env.example .env
   # Edit .env file with your configuration
   ```

4. **Run the application:**
   ```bash
   python run.py
   ```

5. **Access the application:**
   - Open your browser to `http://localhost:5000`
   - The database will be automatically initialized on first run

## Project Structure

```
BibleMemorizer/
├── app.py                 # Main Flask application
├── run.py                 # Development server runner
├── schema.sql             # Database schema
├── requirements.txt       # Python dependencies
├── models/
│   ├── user.py           # User authentication models
│   └── verse.py          # Verse and progress models
├── routes/
│   ├── auth.py           # Authentication routes
│   ├── api.py            # RESTful API endpoints
│   └── admin.py          # Admin/teacher functionality
├── templates/
│   ├── base.html         # Base template
│   └── index.html        # Main application interface
└── instance/             # Database and instance files (created at runtime)
```

## Migration from Firebase

This application replaces the original Firebase backend with a local SQLite solution:

### What's Changed
- **Database:** Firebase → SQLite with comprehensive schema
- **Authentication:** Firebase Auth → Flask-Login with session management
- **APIs:** Firebase SDK → RESTful API endpoints
- **Data Storage:** Real-time database → Structured relational database

### What's Preserved
- **Frontend Experience:** Identical user interface and interactions
- **Scoring Algorithm:** Same fuzzy text matching logic
- **Speech Recognition:** Same browser-based speech recognition
- **Core Functionality:** All memorization features work identically

### Migration Benefits
- **No External Dependencies:** Fully self-contained
- **Enhanced Reporting:** Comprehensive analytics and progress tracking
- **Better Data Structure:** Relational database with proper relationships
- **Advanced Features:** Error analysis, class management, detailed reporting
- **Privacy:** All data stored locally
- **Customization:** Full control over features and data

## API Endpoints

### Authentication
- `POST /auth/login` - User login
- `POST /auth/register` - User registration
- `POST /auth/logout` - User logout
- `GET /auth/current-user` - Get current user info
- `POST /auth/anonymous-session` - Create anonymous session

### Verses
- `GET /api/verses` - Get all verses
- `GET /api/verses/random` - Get random verse
- `GET /api/verses/{id}` - Get specific verse

### Recitations
- `POST /api/recitations` - Submit recitation attempt
- `GET /api/progress/my-progress` - Get current user progress
- `GET /api/attempts/recent` - Get recent attempts

### Admin (Teachers/Admins only)
- `GET /admin/classes` - Manage classes
- `POST /admin/classes` - Create new class
- `GET /admin/reports/class-overview/{id}` - Class reports
- `GET /admin/export/class-data/{id}` - Export class data

## Database Schema

The application uses a comprehensive SQLite schema with the following key tables:

- **users** - Student and teacher accounts
- **classes** - Class organization
- **verses** - Bible verse collection
- **recitation_attempts** - All memorization attempts
- **student_progress** - Aggregated progress tracking
- **recitation_errors** - Detailed error analysis

## Configuration

Key configuration options in `.env`:

```env
SECRET_KEY=your-secret-key-here
FLASK_ENV=development
DATABASE_URL=sqlite:///bible_memorizer.db
```

## Development

### Adding New Verses
1. Use the admin interface (teacher/admin account required)
2. Or directly insert into the `verses` table

### Extending APIs
- Add new routes in the appropriate blueprint files
- Follow the existing pattern for authentication and error handling

### Database Changes
- Modify `schema.sql` for structural changes
- Create migration scripts for existing data

## Production Deployment

### Using Gunicorn
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

### Environment Variables
- Set `FLASK_ENV=production`
- Use a strong `SECRET_KEY`
- Configure appropriate database permissions

### Security Considerations
- Enable HTTPS
- Set secure session cookie flags
- Implement rate limiting
- Regular database backups

## Support

For technical support or feature requests, refer to the admin dashboard or check the application logs for detailed error information.