# Deployment Guide for Render.com

This guide will help you deploy your Flask + React application to Render.com for free.

## Prerequisites

1. **GitHub Repository**: Your code should be in a GitHub repository
2. **Render Account**: Sign up at [render.com](https://render.com)
3. **OpenAI API Key**: For the AI features

## Deployment Steps

### 1. Prepare Your Repository

Make sure all the new configuration files are committed to your GitHub repository:
- `render.yaml` - Main configuration file
- `api/wsgi.py` - Production WSGI entry point
- `api/db_config.py` - Database configuration
- `.env.example` - Environment variables template
- Updated `api/requirements.txt` with gunicorn and psycopg2-binary

### 2. Connect to Render

1. Go to [render.com](https://render.com) and sign up/login
2. Click "New +" and select "Blueprint"
3. Connect your GitHub account and select your repository
4. Render will automatically detect the `render.yaml` file

### 3. Configure Services

The `render.yaml` will create three services:

#### A. Flask API Service
- **Name**: `flask-api`
- **Type**: Web Service
- **Environment**: Python
- **Build Command**: `cd api && pip install -r requirements.txt`
- **Start Command**: `cd api && gunicorn --bind 0.0.0.0:$PORT api:app`

#### B. React Frontend Service  
- **Name**: `react-frontend`
- **Type**: Static Site
- **Build Command**: `npm ci && npm run build`
- **Publish Directory**: `./dist`

#### C. PostgreSQL Database
- **Name**: `postgres-db`
- **Type**: PostgreSQL Database
- **Plan**: Free

### 4. Set Environment Variables

In the Render dashboard, for your Flask API service, add these environment variables:

**Required:**
- `OPENAI_KEY`: Your OpenAI API key (mark as secret)
- `FLASK_ENV`: `production`

**Optional:**
- `CORS_ORIGINS`: Your frontend URL (will be auto-configured)

The `DATABASE_URL` will be automatically provided by the PostgreSQL service.

### 5. Update Service URLs

After deployment, you'll get URLs like:
- Flask API: `https://flask-api-xyz.onrender.com`
- React Frontend: `https://react-frontend-abc.onrender.com`

Update these files with your actual URLs:

#### A. Update `render.yaml` (lines 28, 52):
```yaml
destination: https://your-actual-flask-api-url.onrender.com/api/*
```

#### B. Update `vite.config.js` (line 26):
```javascript
? 'https://your-actual-flask-api-url.onrender.com'
```

#### C. Update `api/api.py` (line 52):
```python
'https://your-actual-react-frontend-url.onrender.com',
```

### 6. Deploy

1. Commit and push the URL updates to GitHub
2. Render will automatically redeploy your services
3. Wait for all services to build and start (can take 5-10 minutes)

## Important Notes

### Free Tier Limitations
- **Sleep Mode**: Services sleep after 15 minutes of inactivity
- **Build Minutes**: Limited build time per month
- **Bandwidth**: 100GB/month outbound transfer

### Database Considerations
- **PostgreSQL**: Replaces SQLite for production
- **USDA Database**: Currently disabled in production (large file)
- **Data Migration**: You may need to seed initial data

### Monitoring
- Check service logs in Render dashboard for debugging
- Health checks are configured for the API service
- Both services will show status in your dashboard

## Testing Your Deployment

1. **API Health Check**: Visit `https://your-flask-api-url.onrender.com/api/time`
2. **Frontend**: Visit `https://your-react-frontend-url.onrender.com`
3. **Full Integration**: Test API calls from frontend

## Troubleshooting

### Common Issues

1. **Build Failures**: Check build logs in Render dashboard
2. **Database Connection**: Verify DATABASE_URL is set correctly
3. **CORS Errors**: Ensure frontend URL is in CORS_ORIGINS
4. **Import Errors**: Check Python path and requirements.txt

### Debug Commands

Add these to temporarily debug issues:

```python
# In api.py, add debugging endpoint
@app.route('/api/debug/env')
def debug_env():
    return {
        'flask_env': os.getenv('FLASK_ENV'),
        'database_url_set': bool(os.getenv('DATABASE_URL')),
        'openai_key_set': bool(os.getenv('OPENAI_KEY')),
    }
```

## Next Steps

After successful deployment:

1. **Custom Domain**: Add your own domain in Render dashboard
2. **SSL Certificate**: Automatically provided by Render
3. **Monitoring**: Set up uptime monitoring
4. **Backups**: Configure database backups
5. **Environment Management**: Separate staging and production

## Cost Optimization

- **Free Tier**: Both services can run on free tier
- **Usage Monitoring**: Track usage to stay within limits
- **Optimization**: Optimize build times and resource usage

## Support

- **Render Docs**: [render.com/docs](https://render.com/docs)
- **Community**: Render Discord/Forums
- **Issues**: Check GitHub repository issues

---

**Note**: Replace placeholder URLs with your actual Render service URLs after first deployment.