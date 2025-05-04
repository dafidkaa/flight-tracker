# Deploying to Digital Ocean

This guide explains how to deploy the Zagreb Airport Flight Tracker application to Digital Ocean.

## Prerequisites

1. A Digital Ocean account
2. Docker installed on your local machine (for testing)
3. Digital Ocean CLI (doctl) installed (optional)

## Deployment Options

There are two main ways to deploy this application to Digital Ocean:

1. **Digital Ocean App Platform** - A fully managed platform (recommended)
2. **Digital Ocean Droplet** - A virtual machine where you have full control

## Option 1: Deploy to Digital Ocean App Platform

### Step 1: Prepare Your Repository

Make sure your code is pushed to a Git repository (GitHub, GitLab, etc.).

### Step 2: Create a New App

1. Log in to your Digital Ocean account
2. Go to the App Platform section
3. Click "Create App"
4. Select your Git repository
5. Select the branch you want to deploy (usually `main`)

### Step 3: Configure Your App

1. Select "Dockerfile" as the deployment method
2. Configure the following environment variables:
   - `PORT`: 8080
   - `ENVIRONMENT`: production
   - `LOG_TO_FILE`: false
   - `RESEND_API_KEY`: Your Resend API key

3. Configure resources:
   - Select an appropriate plan (Basic or Pro)
   - Recommended: At least 1GB RAM and 1 vCPU

4. Configure the app name and region

### Step 4: Deploy

1. Review your settings
2. Click "Create Resources"
3. Wait for the deployment to complete

### Step 5: Access Your App

Once deployed, you can access your app at the URL provided by Digital Ocean.

## Option 2: Deploy to a Digital Ocean Droplet

### Step 1: Create a Droplet

1. Log in to your Digital Ocean account
2. Click "Create" and select "Droplets"
3. Choose an image (Ubuntu 20.04 LTS recommended)
4. Choose a plan (at least 1GB RAM and 1 vCPU)
5. Choose a datacenter region close to your users
6. Add your SSH key
7. Click "Create Droplet"

### Step 2: Connect to Your Droplet

```bash
ssh root@your_droplet_ip
```

### Step 3: Install Docker and Docker Compose

```bash
# Update package lists
apt update

# Install required packages
apt install -y apt-transport-https ca-certificates curl software-properties-common

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -

# Add Docker repository
add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"

# Update package lists again
apt update

# Install Docker
apt install -y docker-ce

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/download/v2.5.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
```

### Step 4: Clone Your Repository

```bash
# Install Git
apt install -y git

# Clone your repository
git clone https://github.com/yourusername/flight-tracker.git
cd flight-tracker
```

### Step 5: Configure Environment Variables

```bash
# Create .env file
cp .env.example .env
nano .env
```

Update the environment variables in the .env file:
- `PORT`: 8080
- `ENVIRONMENT`: production
- `LOG_TO_FILE`: true
- `RESEND_API_KEY`: Your Resend API key

### Step 6: Build and Run the Docker Container

```bash
# Build and start the container
docker-compose up -d

# Check the logs
docker-compose logs -f
```

### Step 7: Set Up Nginx as a Reverse Proxy (Optional)

If you want to use a domain name and HTTPS, you can set up Nginx as a reverse proxy:

```bash
# Install Nginx
apt install -y nginx

# Install Certbot for SSL
apt install -y certbot python3-certbot-nginx

# Configure Nginx
nano /etc/nginx/sites-available/flight-tracker
```

Add the following configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site and restart Nginx:

```bash
ln -s /etc/nginx/sites-available/flight-tracker /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

### Step 8: Set Up SSL (Optional)

```bash
certbot --nginx -d your-domain.com
```

## Maintenance

### Updating the Application

#### For App Platform:

Push changes to your Git repository, and Digital Ocean will automatically deploy the new version.

#### For Droplet:

```bash
cd flight-tracker
git pull
docker-compose down
docker-compose up -d
```

### Monitoring

For both deployment options, you can use Digital Ocean's built-in monitoring tools to keep track of your application's performance.

## Troubleshooting

### Common Issues

1. **Application not starting**: Check the logs with `docker-compose logs`
2. **Cannot connect to the application**: Make sure the port is correctly configured and not blocked by a firewall
3. **Email notifications not working**: Verify your Resend API key is correctly set

### Viewing Logs

#### For App Platform:

View logs in the Digital Ocean dashboard under your app's "Logs" tab.

#### For Droplet:

```bash
docker-compose logs -f
```

## Backup and Restore

### Backing Up Data

The application stores data in the `data` directory. To back up this data:

```bash
tar -czvf flight-tracker-data-backup.tar.gz data/
```

### Restoring Data

```bash
tar -xzvf flight-tracker-data-backup.tar.gz
```
