import sys
import os
import warnings
import logging
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QLabel, QLineEdit, QComboBox,
                           QTableWidget, QTableWidgetItem, QProgressBar, QMessageBox,
                           QFileDialog, QMenu, QInputDialog)
# Add these imports
import requests
from bs4 import BeautifulSoup
import re
import urllib.parse

# Set up logging
log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'business_finder.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

# Suppress PyQt6 SIP deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="PyQt6")
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPoint
from PyQt6.QtGui import QAction
import csv
import folium
from folium.plugins import MarkerCluster
import webbrowser
from geopy.geocoders import Nominatim
import requests
import json
import overpy
import time

class BusinessFinderThread(QThread):
    progress = pyqtSignal(int, int, str)
    result = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, location, radius, business_type):
        super().__init__()
        self.location = location
        self.radius = radius
        self.business_type = business_type
        
    def run(self):
        try:
            # Get coordinates using Nominatim with better error handling and state support
            logging.info(f"Starting search for: {self.location}")
            geolocator = Nominatim(
                user_agent="business_finder",
                timeout=10  # Increase timeout to 10 seconds
            )
            
            try:
                # Try to get more specific location by adding state if not already included
                if ',' not in self.location:
                    # Try with state abbreviation
                    location = geolocator.geocode(f"{self.location}, CO")
                    if not location:
                        # Try with full state name
                        location = geolocator.geocode(f"{self.location}, Colorado")
                else:
                    location = geolocator.geocode(self.location)
                
                if not location:
                    self.error.emit(f"Could not find coordinates for: {self.location}")
                    logging.error(f"Failed to find coordinates for: {self.location}")
                    return
                    
                lat, lon = location.latitude, location.longitude
                logging.info(f"Found coordinates: {lat}, {lon}")
            except Exception as e:
                self.error.emit(f"Error getting location coordinates: {str(e)}")
                logging.error(f"Error getting coordinates: {str(e)}")
                return
            
            # Create Overpass API query
            api = overpy.Overpass()
            
            # Convert radius from km to m
            radius_m = self.radius * 1000
            
            # Simple query to find ALL nodes with names
            query = f"""
                [out:json][timeout:25];
                (
                    node["name"](around:{radius_m},{lat},{lon});
                );
                out body;
            """
            
            # Log the query being used
            logging.info(f"Using Overpass query:\n{query}")
            
            # Execute Overpass query with retry mechanism
            max_retries = 3
            retry_delay = 5  # seconds
            
            for attempt in range(max_retries):
                try:
                    logging.info(f"Attempting Overpass query (attempt {attempt + 1}/{max_retries})")
                    result = api.query(query)
                    logging.info(f"Successfully got Overpass response with {len(result.nodes)} nodes and {len(result.ways)} ways")
                    break
                except Exception as e:
                    logging.error(f"Overpass query attempt {attempt + 1} failed: {str(e)}")
                    if attempt == max_retries - 1:  # Last attempt
                        self.error.emit(f"Failed to get business data after {max_retries} attempts: {str(e)}")
                        logging.error(f"Failed after all retries. Last error: {str(e)}")
                        return
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
            
            businesses = []
            
            # Process nodes - list EVERY node with a name
            logging.info(f"Processing {len(result.nodes)} nodes")
            for i, node in enumerate(result.nodes):
                try:
                    # Get all tags from the node
                    tags = node.tags
                    
                    # Log node tags for debugging
                    logging.info(f"Node {i} tags: {tags}")
                    
                    # If node has a name, treat it as a business
                    if 'name' in tags:
                        # Determine category based on available tags
                        category = 'unknown'
                        if tags.get('amenity'):
                            category = tags.get('amenity')
                        elif tags.get('shop'):
                            category = tags.get('shop')
                        elif tags.get('office'):
                            category = tags.get('office')
                        elif tags.get('leisure'):
                            category = tags.get('leisure')
                        elif tags.get('tourism'):
                            category = tags.get('tourism')
                        
                        # Create business info
                        business_info = {
                            'name': tags.get('name'),
                            'address': tags.get('addr:street', '') + ' ' + tags.get('addr:housenumber', ''),
                            'category': category,
                            'website': tags.get('website', '') or None,
                            'latitude': node.lat,
                            'longitude': node.lon,
                            'incomplete': False
                        }
                        
                        # Add business
                        businesses.append(business_info)
                        
                        self.progress.emit(len(businesses), len(result.nodes), 
                                         f"Processing nodes: {i+1}/{len(result.nodes)}")
                        
                        # Log business info
                        website_status = "Has Website" if business_info['website'] else "No Website"
                        logging.info(f"Added business: {business_info['name']} ({category}) - {website_status}")
                    else:
                        logging.info(f"Skipping node {i} - no name tag")
                        
                except Exception as e:
                    logging.error(f"Error processing node {i}: {str(e)}")
            

            
            # Filter out duplicates
            unique_businesses = []
            seen_names = set()
            for business in businesses:
                if business['name'] not in seen_names:
                    seen_names.add(business['name'])
                    unique_businesses.append(business)
            businesses = unique_businesses
            
            self.result.emit({
                'businesses': businesses,
                'location': {'lat': lat, 'lon': lon}
            })
            
        except Exception as e:
            self.error.emit(str(e))

class BusinessFinderApp(QMainWindow):
    error = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Local Business Website Checker")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create top bar
        top_bar = QHBoxLayout()
        layout.addLayout(top_bar)
        
        # Location input
        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("Enter location or allow geolocation")
        top_bar.addWidget(self.location_input)
        
        # Search radius
        self.radius_input = QLineEdit()
        self.radius_input.setPlaceholderText("Search radius (km)")
        self.radius_input.setText("5")
        top_bar.addWidget(self.radius_input)
        
        # Business type
        self.business_type = QComboBox()
        self.business_type.addItems([
            "restaurants",
            "shops",
            "all amenities"
        ])
        top_bar.addWidget(self.business_type)
        
        # Search button
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.start_search)
        top_bar.addWidget(self.search_button)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7)
        self.results_table.setHorizontalHeaderLabels([
            "Name", "Address", "Category", "Website Status", 
                "Social Media", "Website Status Detail", "Data Status"
        ])
        
        # Add a filter for incomplete data
        self.filter_incomplete = QPushButton("Show Incomplete Only")
        self.filter_incomplete.setCheckable(True)
        self.filter_incomplete.clicked.connect(self.filter_results)
        top_bar.addWidget(self.filter_incomplete)
        layout.addWidget(self.results_table)
        
        # Map container
        self.map_container = QLabel()
        self.map_container.setMinimumHeight(400)
        layout.addWidget(self.map_container)
        
        # Export button
        export_button = QPushButton("Export to CSV")
        export_button.clicked.connect(self.export_to_csv)
        layout.addWidget(export_button)
        
        # Add a batch search button
        batch_button = QPushButton("Batch Search Missing Websites")
        batch_button.clicked.connect(self.batch_search_websites)
        layout.addWidget(batch_button)
        
        # Create thread
        self.search_thread = None
        
        # Add context menu to table
        self.results_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results_table.customContextMenuRequested.connect(self.show_context_menu)
        
        # Make table cells editable with double-click (for website URLs)
        self.results_table.cellDoubleClicked.connect(self.edit_cell)
        
    def start_search(self):
        try:
            if self.search_thread and self.search_thread.isRunning():
                return
                
            location = self.location_input.text()
            if not location:
                self.error.emit("Please enter a location")
                return
                
            try:
                radius = float(self.radius_input.text())
            except ValueError:
                self.error.emit("Please enter a valid radius")
                return
                
            self.search_thread = BusinessFinderThread(
                location=location,
                radius=radius,
                business_type=self.business_type.currentText()
            )
            
            self.search_thread.result.connect(self.display_results)
            self.search_thread.progress.connect(self.update_progress)
            self.search_thread.error.connect(self.show_error)
            self.error.connect(self.show_error)
            self.search_thread.start()
            
        except Exception as e:
            # Log the error
            logging.error(f"Error starting search: {str(e)}")
            # Show user-friendly error message
            self.error.emit(f"Error starting search: {str(e)}")
            return
        
    def update_progress(self, count, total=None, message=None):
        if total:
            self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(count)
        if message:
            self.statusBar().showMessage(message)
            QApplication.processEvents()  # Force UI update

    def display_results(self, results):
        try:
            businesses = results['businesses']
            location = results['location']
            
            # Update table
            self.results_table.setRowCount(len(businesses))
            if not businesses:
                # Create a more user-friendly error message with available location info
                location_info = []
                if 'name' in location:
                    location_info.append(f"Location: {location['name']}")
                if 'radius' in location:
                    location_info.append(f"Radius: {location['radius']}km")
                if 'business_type' in location:
                    location_info.append(f"Business type: {location['business_type']}")
                
                location_str = "\n".join(location_info)
                self.error.emit(f"No businesses found in this area.\n" +
                              f"{location_str}\n" +
                              "Try adjusting the search radius or business type.")
                return
                
            # Set table to have 7 columns
            self.results_table.setColumnCount(7)
            self.results_table.setHorizontalHeaderLabels([
                "Name", "Address", "Category", "Website Status", 
                "Social Media", "Website Status Detail", "Data Status"
            ])
                
            for row, business in enumerate(businesses):
                self.results_table.setItem(row, 0, QTableWidgetItem(business['name']))
                self.results_table.setItem(row, 1, QTableWidgetItem(business['address']))
                self.results_table.setItem(row, 2, QTableWidgetItem(business['category']))
                
                # Website status
                website_status = "No Website" if not business['website'] else "Has Website"
                self.results_table.setItem(row, 3, QTableWidgetItem(website_status))
                
                # Fill in additional columns with placeholders or actual data
                self.results_table.setItem(row, 4, QTableWidgetItem(""))  # Social Media
                self.results_table.setItem(row, 5, QTableWidgetItem(business['website'] or ""))  # Website Status Detail
                
                # Data status - mark as complete if it has a website
                data_completeness = "Complete" if business['website'] else "Incomplete"
                self.results_table.setItem(row, 6, QTableWidgetItem(data_completeness))
            
            # Filter results if needed
            self.filter_results()
            
            # Show success message
            QMessageBox.information(self, "Success", 
                f"Found {len(businesses)} businesses.\n" +
                f"{sum(1 for b in businesses if not b['website'])} businesses without websites.")
            
            # Create map
            m = folium.Map(location=[location['lat'], location['lon']], zoom_start=13)
            marker_cluster = MarkerCluster().add_to(m)
            
            for business in businesses:
                if business.get('latitude') and business.get('longitude'):
                    folium.Marker(
                        location=[business['latitude'], business['longitude']],
                        popup=f"{business['name']}\n{business['address']}",
                        icon=folium.Icon(color='red' if not business['website'] else 'green')
                    ).add_to(marker_cluster)
            
            # Save map to HTML and open in browser
            map_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'map.html')
            m.save(map_file)
            webbrowser.open('file://' + map_file)
            
        except Exception as e:
            # Log the error
            logging.error(f"Error displaying results: {str(e)}")
            # Show user-friendly error message
            self.error.emit(f"Error displaying results: {str(e)}")
            return

    def show_error(self, error):
        # Log the error
        logging.error(f"Error occurred: {error}")
        
        # Show error message in a dialog
        error_dialog = QMessageBox(self)
        error_dialog.setIcon(QMessageBox.Icon.Critical)
        error_dialog.setWindowTitle("Error")
        error_dialog.setText(error)
        error_dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        error_dialog.exec()
        
    def filter_results(self):
        show_incomplete_only = self.filter_incomplete.isChecked()
        
        for row in range(self.results_table.rowCount()):
            # Make sure we only check columns that exist
            if self.results_table.columnCount() <= 3:  # We only have 4 columns now (0-3)
                # Just use website_status to determine completeness
                website_status = self.results_table.item(row, 3)
                if website_status:
                    is_complete = website_status.text() != "No Website"
                    if show_incomplete_only and is_complete:
                        self.results_table.setRowHidden(row, True)
                    else:
                        self.results_table.setRowHidden(row, False)
            else:
                # Original code for when we have more columns
                data_status = self.results_table.item(row, 6)
                if data_status:
                    if show_incomplete_only and data_status.text() == "Complete":
                        self.results_table.setRowHidden(row, True)
                    else:
                        self.results_table.setRowHidden(row, False)

    def export_to_csv(self):
        try:
            file_name, _ = QFileDialog.getSaveFileName(
                self, "Save CSV", "businesses.csv", "CSV Files (*.csv)"
            )
            if file_name:
                businesses = []
                for row in range(self.results_table.rowCount()):
                    if not self.results_table.isRowHidden(row):
                        business = {
                            'name': self.results_table.item(row, 0).text(),
                            'address': self.results_table.item(row, 1).text(),
                            'category': self.results_table.item(row, 2).text(),
                            'website': self.results_table.item(row, 3).text(),
                            'social_media': self.results_table.item(row, 4).text(),
                            'website_status': self.results_table.item(row, 5).text(),
                            'data_status': self.results_table.item(row, 6).text()
                        }
                        businesses.append(business)
                        
                # Write to CSV using csv writer
                with open(file_name, 'w', newline='') as f:
                    writer = csv.writer(f)
                    # Write header
                    writer.writerow(['name', 'address', 'category', 'website', 'social_media', 'website_status', 'data_status'])
                    # Write data
                    for business in businesses:
                        writer.writerow([
                            business['name'],
                            business['address'],
                            business['category'],
                            business['website'],
                            business['social_media'],
                            business['website_status'],
                            business['data_status']
                        ])
                QMessageBox.information(self, "Success", "CSV file has been saved!")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export CSV: {str(e)}")

    def show_context_menu(self, position):
        menu = QMenu()
        
        # Get current row
        row = self.results_table.rowAt(position.y())
        if row < 0:
            return
            
        # Get business info
        business_name = self.results_table.item(row, 0).text()
        website_status = self.results_table.item(row, 3).text() if self.results_table.item(row, 3) else ""
        
        # Add search action
        search_action = menu.addAction(f"Open browser search for '{business_name}'")
        search_action.triggered.connect(lambda: self.search_web_for_business(row))
        
        # Add automated find website action
        if website_status == "No Website":
            find_website_action = menu.addAction(f"Find website for '{business_name}'")
            find_website_action.triggered.connect(lambda: self.auto_find_website(row))
        
        # Add edit website action
        edit_action = menu.addAction("Edit website URL")
        edit_action.triggered.connect(lambda: self.edit_cell(row, 5))  # Column 5 is Website Status Detail
        
        # Show the menu
        menu.exec(self.results_table.mapToGlobal(position))

    def auto_find_website(self, row):
        """Find website for a single business"""
        business_name = self.results_table.item(row, 0).text()
        address = self.results_table.item(row, 1).text() if self.results_table.item(row, 1) else ""
        
        self.statusBar().showMessage(f"Searching for website for {business_name}...")
        QApplication.processEvents()
        
        website = self.find_website_for_business(business_name, address)
        
        if website:
            # Update the table
            self.results_table.setItem(row, 5, QTableWidgetItem(website))
            self.results_table.setItem(row, 3, QTableWidgetItem("Has Website"))
            self.results_table.setItem(row, 6, QTableWidgetItem("Complete"))
            
            # Apply filtering
            self.filter_results()
            
            QMessageBox.information(self, "Website Found", f"Found website for {business_name}:\n{website}")
        else:
            QMessageBox.information(self, "No Website Found", f"Could not find website for {business_name}.")
        
        self.statusBar().showMessage("")

    def search_web_for_business(self, row):
        business_name = self.results_table.item(row, 0).text()
        address = self.results_table.item(row, 1).text() if self.results_table.item(row, 1) else ""
        
        # Create search query with business name and address
        search_query = f"{business_name} {address} website"
        
        # URL encode the query
        import urllib.parse
        encoded_query = urllib.parse.quote_plus(search_query)
        
        # Open search in default web browser
        search_url = f"https://www.bing.com/search?q={encoded_query}"
        webbrowser.open(search_url)
        
        self.statusBar().showMessage(f"Opened web search for {business_name}")

    def edit_cell(self, row, column):
        # Only allow editing website URL (column 5)
        if column == 5:
            current_value = self.results_table.item(row, column).text() if self.results_table.item(row, column) else ""
            business_name = self.results_table.item(row, 0).text()
            
            new_value, ok = QInputDialog.getText(
                self, 
                "Edit Website URL", 
                f"Enter website URL for {business_name}:",
                QLineEdit.EchoMode.Normal,
                current_value
            )
            
            if ok and new_value:
                # Update the cell
                self.results_table.setItem(row, column, QTableWidgetItem(new_value))
                
                # Update website status column (column 3)
                website_status = "Has Website" if new_value else "No Website"
                self.results_table.setItem(row, 3, QTableWidgetItem(website_status))
                
                # Update data status column (column 6)
                data_status = "Complete" if new_value else "Incomplete"
                self.results_table.setItem(row, 6, QTableWidgetItem(data_status))
                
                # Apply filtering
                self.filter_results()
                
                self.statusBar().showMessage(f"Updated website for {business_name}")

    def batch_search_websites(self):
        """Automatically search for websites for all businesses without websites"""
        if self.results_table.rowCount() == 0:
            return
            
        missing_websites = []
        
        # Collect all businesses missing websites
        for row in range(self.results_table.rowCount()):
            website_status = self.results_table.item(row, 3)
            if website_status and website_status.text() == "No Website":
                business_name = self.results_table.item(row, 0).text()
                address = self.results_table.item(row, 1).text() if self.results_table.item(row, 1) else ""
                missing_websites.append((row, business_name, address))
        
        if not missing_websites:
            QMessageBox.information(self, "No Missing Websites", 
                                 "All businesses have website information!")
            return
        
        # Ask for confirmation
        result = QMessageBox.question(
            self, 
            "Batch Website Search",
            f"This will automatically search for websites for {len(missing_websites)} businesses.\n\n" +
            "Note: This uses web scraping which may be slow or get temporarily blocked. " +
            "For production use, consider a proper search API.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if result == QMessageBox.StandardButton.Yes:
            found_count = 0
            self.progress_bar.setMaximum(len(missing_websites))
            
            for i, (row, business_name, address) in enumerate(missing_websites):
                # Update progress
                self.progress_bar.setValue(i + 1)
                self.statusBar().showMessage(f"Searching for websites: {i+1}/{len(missing_websites)}")
                QApplication.processEvents()  # Keep UI responsive
                
                # Search for website
                website = self.find_website_for_business(business_name, address)
                
                if website:
                    # Update the table with found website
                    self.results_table.setItem(row, 5, QTableWidgetItem(website))
                    self.results_table.setItem(row, 3, QTableWidgetItem("Has Website"))
                    self.results_table.setItem(row, 6, QTableWidgetItem("Complete"))
                    found_count += 1
                    
                # Small delay to avoid excessive requests
                time.sleep(1)
            
            # Apply filtering
            self.filter_results()
            
            # Show results
            QMessageBox.information(
                self,
                "Batch Search Complete",
                f"Found websites for {found_count} out of {len(missing_websites)} businesses.\n\n" +
                "You can manually search for the remaining ones using the context menu."
            )

    def find_website_for_business(self, business_name, address=""):
        """Search for business website without opening a browser"""
        try:
            # Format search query
            search_query = f"{business_name} {address} official website"
            
            # URL encode the query
            encoded_query = urllib.parse.quote_plus(search_query)
            
            # Use DuckDuckGo which is more scraper-friendly
            search_url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
            
            # Set a user agent to mimic a browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # Make the request
            response = requests.get(search_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                # Parse the HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find all result links
                results = soup.find_all('a', class_='result__url')
                
                # Extract potential website URLs
                websites = []
                for result in results[:5]:  # Check top 5 results
                    href = result.get('href', '')
                    if href:
                        # Parse URL to get domain
                        try:
                            parsed_url = urllib.parse.urlparse(href)
                            domain = parsed_url.netloc
                            
                            # Skip search engines and common non-business sites
                            skip_domains = ['google.com', 'bing.com', 'yahoo.com', 'youtube.com', 
                                            'facebook.com', 'wikipedia.org', 'yelp.com', 'duckduckgo.com']
                            if domain and not any(skip in domain for skip in skip_domains):
                                # Check if domain contains business name (case insensitive)
                                if re.search(re.escape(business_name.lower()), domain.lower()):
                                    # This is likely the official website
                                    full_url = f"{parsed_url.scheme}://{domain}{parsed_url.path}"
                                    websites.append(full_url)
                                    break
                                else:
                                    # Add to potential websites
                                    websites.append(href)
                        except:
                            continue
                
                # Return first potential website if found
                if websites:
                    return websites[0]
            
            # No website found
            return None
        
        except Exception as e:
            logging.error(f"Error finding website for {business_name}: {str(e)}")
            return None

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = BusinessFinderApp()
    window.show()
    sys.exit(app.exec())