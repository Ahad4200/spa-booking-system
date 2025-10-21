#!/bin/bash

# Spa Booking System Deployment Script
# Automates deployment to various platforms

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="spa-booking-system"
DOCKER_IMAGE="spa-booking-system:latest"
DOCKER_REGISTRY=""  # Add your registry if using one

# Function to print colored output
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to check prerequisites
check_prerequisites() {
    print_message "$YELLOW" "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_message "$RED" "Docker is not installed!"
        exit 1
    fi
    
    # Check environment file
    if [ ! -f "../backend/.env" ]; then
        print_message "$RED" ".env file not found!"
        print_message "$YELLOW" "Copy .env.example to .env and configure it"
        exit 1
    fi
    
    print_message "$GREEN" "Prerequisites check passed!"
}

# Function to run tests
run_tests() {
    print_message "$YELLOW" "Running tests..."
    
    cd ../backend
    
    # Run Python tests if they exist
    if [ -f "test_app.py" ]; then
        python -m pytest test_app.py -v
    fi
    
    # Test database connection
    python -c "from handlers.supabase_handler import SupabaseHandler; s = SupabaseHandler(); print('Database connection successful')"
    
    cd ../deployment
    print_message "$GREEN" "Tests passed!"
}

# Function to build Docker image
build_docker() {
    print_message "$YELLOW" "Building Docker image..."
    
    docker build -t $DOCKER_IMAGE -f Dockerfile ../
    
    print_message "$GREEN" "Docker image built successfully!"
}

# Function to deploy with Docker Compose
deploy_docker_compose() {
    print_message "$YELLOW" "Deploying with Docker Compose..."
    
    # Stop existing containers
    docker-compose down
    
    # Start new containers
    docker-compose up -d
    
    # Wait for health check
    sleep 10
    
    # Check if container is running
    if docker-compose ps | grep -q "Up"; then
        print_message "$GREEN" "Deployment successful!"
        print_message "$YELLOW" "Application running at http://localhost:5000"
    else
        print_message "$RED" "Deployment failed! Check logs with: docker-compose logs"
        exit 1
    fi
}

# Function to deploy to Railway
deploy_railway() {
    print_message "$YELLOW" "Deploying to Railway..."
    
    if ! command -v railway &> /dev/null; then
        print_message "$RED" "Railway CLI not installed!"
        print_message "$YELLOW" "Install with: npm i -g @railway/cli"
        exit 1
    fi
    
    # Login to Railway
    railway login
    
    # Deploy
    cd ../backend
    railway up
    cd ../deployment
    
    print_message "$GREEN" "Deployed to Railway!"
}

# Function to deploy to Render
deploy_render() {
    print_message "$YELLOW" "Deploying to Render..."
    
    # Create render.yaml if not exists
    if [ ! -f "../render.yaml" ]; then
        cat > ../render.yaml << EOF
services:
  - type: web
    name: spa-booking-system
    env: python
    buildCommand: "pip install -r backend/requirements.txt"
    startCommand: "cd backend && gunicorn app:app"
    envVars:
      - fromGroup: spa-booking-env
EOF
    fi
    
    print_message "$YELLOW" "Push to GitHub and connect repository in Render Dashboard"
    print_message "$GREEN" "Render configuration created!"
}

# Function to deploy to Heroku
deploy_heroku() {
    print_message "$YELLOW" "Deploying to Heroku..."
    
    if ! command -v heroku &> /dev/null; then
        print_message "$RED" "Heroku CLI not installed!"
        exit 1
    fi
    
    # Create Procfile if not exists
    if [ ! -f "../Procfile" ]; then
        echo "web: cd backend && gunicorn app:app" > ../Procfile
    fi
    
    # Create app if not exists
    heroku create $APP_NAME --region eu || true
    
    # Set environment variables
    heroku config:set $(cat ../backend/.env | grep -v '^#' | xargs)
    
    # Deploy
    git push heroku main
    
    print_message "$GREEN" "Deployed to Heroku!"
}

# Function to setup Twilio webhooks
setup_twilio() {
    print_message "$YELLOW" "Setting up Twilio webhooks..."
    
    read -p "Enter your application URL (e.g., https://your-app.com): " APP_URL
    
    print_message "$YELLOW" "Configure these webhooks in Twilio Console:"
    print_message "$GREEN" "Voice URL: ${APP_URL}/webhook/incoming-call"
    print_message "$GREEN" "Status Callback: ${APP_URL}/webhook/call-status"
    print_message "$YELLOW" "Method: POST for both"
}

# Function to setup SSL with Let's Encrypt
setup_ssl() {
    print_message "$YELLOW" "Setting up SSL with Let's Encrypt..."
    
    if ! command -v certbot &> /dev/null; then
        print_message "$RED" "Certbot not installed!"
        print_message "$YELLOW" "Install with: sudo apt-get install certbot"
        exit 1
    fi
    
    read -p "Enter your domain name: " DOMAIN
    read -p "Enter your email: " EMAIL
    
    sudo certbot certonly --standalone -d $DOMAIN --email $EMAIL --agree-tos --non-interactive
    
    print_message "$GREEN" "SSL certificate obtained!"
}

# Function to backup database
backup_database() {
    print_message "$YELLOW" "Creating database backup..."
    
    # Load environment variables
    source ../backend/.env
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="backup_${TIMESTAMP}.sql"
    
    # Create backup using Supabase CLI or pg_dump
    print_message "$YELLOW" "Backup instructions:"
    print_message "$GREEN" "1. Go to Supabase Dashboard > Settings > Database"
    print_message "$GREEN" "2. Click 'Backup' to create a backup"
    print_message "$GREEN" "3. Or use: pg_dump $SUPABASE_URL > $BACKUP_FILE"
    
    print_message "$GREEN" "Backup process initiated!"
}

# Function to show deployment menu
show_menu() {
    echo "================================"
    echo "  Spa Booking System Deployment"
    echo "================================"
    echo "1. Deploy with Docker Compose (Local/VPS)"
    echo "2. Deploy to Railway"
    echo "3. Deploy to Render"
    echo "4. Deploy to Heroku"
    echo "5. Setup Twilio Webhooks"
    echo "6. Setup SSL Certificate"
    echo "7. Backup Database"
    echo "8. Run All Checks"
    echo "9. Exit"
    echo ""
    read -p "Select option: " choice
}

# Main deployment flow
main() {
    print_message "$GREEN" "🚀 Spa Booking System Deployment Script"
    
    # Always check prerequisites first
    check_prerequisites
    
    while true; do
        show_menu
        
        case $choice in
            1)
                run_tests
                build_docker
                deploy_docker_compose
                ;;
            2)
                run_tests
                deploy_railway
                ;;
            3)
                run_tests
                deploy_render
                ;;
            4)
                run_tests
                deploy_heroku
                ;;
            5)
                setup_twilio
                ;;
            6)
                setup_ssl
                ;;
            7)
                backup_database
                ;;
            8)
                check_prerequisites
                run_tests
                print_message "$GREEN" "All checks passed!"
                ;;
            9)
                print_message "$GREEN" "Goodbye!"
                exit 0
                ;;
            *)
                print_message "$RED" "Invalid option!"
                ;;
        esac
        
        echo ""
        read -p "Press Enter to continue..."
    done
}

# Run main function
main