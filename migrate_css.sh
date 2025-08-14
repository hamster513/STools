#!/bin/bash

# CSS Migration Script for STools Project
# This script migrates from old monolithic CSS files to new modular structure

set -e

echo "🚀 Starting CSS migration to modular structure..."

# Create backup directory
BACKUP_DIR="css_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "📦 Creating backup in $BACKUP_DIR..."

# Backup old CSS files
if [ -f "static/css/style.css" ]; then
    cp "static/css/style.css" "$BACKUP_DIR/static_style.css"
    echo "  ✓ Backed up static/css/style.css"
fi

if [ -f "auth/static/css/style.css" ]; then
    cp "auth/static/css/style.css" "$BACKUP_DIR/auth_style.css"
    echo "  ✓ Backed up auth/static/css/style.css"
fi

if [ -f "vulnanalizer/app/static/css/style.css" ]; then
    cp "vulnanalizer/app/static/css/style.css" "$BACKUP_DIR/vulnanalizer_style.css"
    echo "  ✓ Backed up vulnanalizer/app/static/css/style.css"
fi

if [ -f "loganalizer/app/static/css/style.css" ]; then
    cp "loganalizer/app/static/css/style.css" "$BACKUP_DIR/loganalizer_style.css"
    echo "  ✓ Backed up loganalizer/app/static/css/style.css"
fi

echo "🔄 Updating HTML templates to use new CSS structure..."

# Update vulnanalizer template
if [ -f "vulnanalizer/app/templates/index.html" ]; then
    sed -i.bak 's|href="/static/css/style.css?v=[0-9.]*"|href="/static/css/main.css?v=4.0"|g' "vulnanalizer/app/templates/index.html"
    echo "  ✓ Updated vulnanalizer/app/templates/index.html"
fi

# Update loganalizer template
if [ -f "loganalizer/app/templates/index.html" ]; then
    sed -i.bak 's|href="/static/css/style.css?v=[0-9.]*"|href="/static/css/main.css?v=4.0"|g' "loganalizer/app/templates/index.html"
    echo "  ✓ Updated loganalizer/app/templates/index.html"
fi

# Update auth templates
if [ -f "auth/templates/login.html" ]; then
    sed -i.bak 's|href="/static/css/style.css"|href="/static/css/main.css?v=4.0"|g' "auth/templates/login.html"
    echo "  ✓ Updated auth/templates/login.html"
fi

if [ -f "auth/templates/users.html" ]; then
    sed -i.bak 's|href="/static/css/style.css"|href="/static/css/main.css?v=4.0"|g' "auth/templates/users.html"
    echo "  ✓ Updated auth/templates/users.html"
fi

echo "🔧 Updating FastAPI routes to serve new CSS..."

# Update vulnanalizer main.py to serve main.css
if [ -f "vulnanalizer/app/main.py" ]; then
    # Add route for main.css if not exists
    if ! grep -q "main.css" "vulnanalizer/app/main.py"; then
        # Find the existing style.css route and replace it
        sed -i.bak '/style.css/,+3d' "vulnanalizer/app/main.py"
        echo "  ✓ Updated vulnanalizer/app/main.py"
    fi
fi

echo "📊 CSS Structure Summary:"
echo "  📁 static/css/"
echo "    ├── 📁 base/"
echo "    │   ├── variables.css     (CSS variables and themes)"
echo "    │   ├── reset.css         (CSS reset and base styles)"
echo "    │   └── layout.css        (Grid-based layout system)"
echo "    ├── 📁 components/"
echo "    │   ├── buttons.css       (Button components)"
echo "    │   ├── tables.css        (Table components)"
echo "    │   └── forms.css         (Form components)"
echo "    ├── 📁 pages/"
echo "    │   ├── auth.css          (Auth page styles)"
echo "    │   ├── vulnanalizer.css  (VulnAnalizer page styles)"
echo "    │   └── loganalizer.css   (LogAnalizer page styles)"
echo "    └── main.css              (Main import file)"

echo ""
echo "✅ Migration completed successfully!"
echo ""
echo "📋 Next steps:"
echo "  1. Test the application to ensure styles are working"
echo "  2. Remove old CSS files if everything works correctly"
echo "  3. Update any component-specific styles as needed"
echo ""
echo "💾 Backup files are stored in: $BACKUP_DIR"
echo "🔄 To rollback, restore files from the backup directory"
