# Company Finder

A PyQt6 desktop application for discovering local businesses and analyzing their online presence. This tool helps users identify businesses that lack websites or online presence, making it valuable for digital marketing professionals and local business outreach.

## Features

- **Business Discovery**: Search for businesses by location name and radius
- **Website Analysis**: Automatically check which businesses have websites
- **Batch Website Finder**: Programmatically search for websites for businesses that don't have them listed
- **Interactive Map**: View all discovered businesses on an interactive map with color coding
- **Data Export**: Export business data to CSV for further analysis
- **Filtering**: Filter businesses by those missing websites
- **Manual Updates**: Easily update business information with context menu options

## Screenshots

_[Add screenshots of your application here]_

## Requirements

- Python 3.8+
- PyQt6
- Internet connection for map generation and website searching

## Setup

1. Clone the repository:
   git clone https://github.com/yourusername/CompanyFinder.git cd CompanyFinder

2. Create a virtual environment:
   python -m venv .venv

3. Activate the virtual environment:

- Linux/Mac: `source .venv/bin/activate`
- Windows: `.venv\Scripts\activate`

4. Install dependencies:
   pip install -r requirements.txt

5. Run the application:
   python src/main.py

## Usage Guide

1. **Search for Businesses**:

- Enter a location (city, address, etc.)
- Set a search radius in kilometers
- Select business type
- Click "Search"

2. **Working with Results**:

- The table shows all businesses found
- Click "Show Incomplete Only" to filter those missing websites
- Right-click on a business to search for its website or edit details
- Double-click on website fields to edit them

3. **Batch Processing**:

- Click "Batch Search Missing Websites" to automatically search for all missing websites

4. **Export Data**:

- Click "Export to CSV" to save your business data

## Troubleshooting

- If the map doesn't load, check your internet connection
- If batch website search isn't working, there might be rate limiting from search providers

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[Choose an appropriate license for your project]

## Acknowledgments

- OpenStreetMap for business data
- Folium for map integration
