import json
import os
from dash import Dash, html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import requests
from flask import send_from_directory

from dash_mcp_showcase.processing_agent import ProcessingAgent


dash_app = Dash(
    external_scripts=[
        "https://cdnjs.cloudflare.com/ajax/libs/require.js/2.3.6/require.min.js",
        "https://cdnjs.cloudflare.com/ajax/libs/require.js/2.3.6/require.min.js.map"
    ],
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)

# Add static file serving for local development
@dash_app.server.route('/data/<path:filename>')
def serve_data(filename):
    """Serve data files for local development"""
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
    return send_from_directory(data_dir, filename)

BASE_URL = os.getenv('SERVER_BASE_URL', '/')
agent = ProcessingAgent()

dash_app.layout = html.Div([
    html.Div([
        html.H1("Dash MCP Showcase - API Communication Demo"),
        html.Div([
            html.Div([
                html.Label("Year:"),
                dcc.Dropdown(id='year-dropdown'),
            ], className='col-md-6'),
            html.Div([
                html.Label("Quarter:"),
                dcc.Dropdown(id='quarter-dropdown'),
            ], className='col-md-6'),
        ], className='row mb-3')
    ], className='container text-center mb-4'),
    
    html.Hr(),
    
    dcc.Loading(html.Div(id='report-section', className='container mt-4')),
    dcc.Location(id='url', refresh=False),
], className='container-fluid py-4')


@callback(
    Output('year-dropdown', 'options'),
    Input('url', 'pathname')
)
def update_year_dropdown(pathname):
    """Fetch available years from the filters API endpoint."""
    try:
        endpoint = 'data/filters.json'
        response = requests.get(f"{BASE_URL.rstrip('/')}/{endpoint}")
        response.raise_for_status()  # Raises an HTTPError for bad responses
        years = response.json()
        return [{'label': year, 'value': year} for year in years.keys()]
    except requests.RequestException as e:
        print(f"Error fetching years: {e}")
        return [{'label': 'Error loading data', 'value': 'error'}]

@callback(
    Output('quarter-dropdown', 'options'),
    Input('year-dropdown', 'value')
)
def update_quarter_dropdown(selected_year):
    """Fetch available quarters for the selected year from the filters API."""
    if not selected_year or selected_year == 'error':
        return []
    
    try:
        endpoint = 'data/filters.json'
        response = requests.get(f"{BASE_URL.rstrip('/')}/{endpoint}")
        response.raise_for_status()
        quarters_data = response.json()
        quarters = quarters_data.get(selected_year, [])
        return [{'label': quarter, 'value': quarter} for quarter in quarters]
    except requests.RequestException as e:
        print(f"Error fetching quarters: {e}")
        return [{'label': 'Error loading data', 'value': 'error'}]

@callback(
    Output('report-section', 'children'),
    Input('year-dropdown', 'value'),
    Input('quarter-dropdown', 'value')
)
def get_report_data(selected_year, selected_quarter):
    """Fetch report data from the reports API and process it with OpenAI."""
    if not selected_year or not selected_quarter:
        return "Please select a year and quarter to get the report data."
    
    if selected_year == 'error' or selected_quarter == 'error':
        return "Error: Unable to load data from API endpoints."
    
    try:
        # Demonstrate API communication by fetching report data
        endpoint = "data/reports.json"
        response = requests.get(f"{BASE_URL.rstrip('/')}/{endpoint}")
        response.raise_for_status()
        
        response_data = response.json()
        report_data = response_data.get(selected_year, {}).get(selected_quarter, "No data available for this selection.")
        
        if isinstance(report_data, dict):
            # Showcase: Use OpenAI API to process the data
            markdown_output = agent.json_to_markdown(report_data)
            return html.Div([
                html.H3("📊 Report Data Processing Results"),
                html.P("Data fetched from API and processed using OpenAI integration:"),
                dcc.Markdown(markdown_output)
            ])
        else:
            return html.Div([
                html.H3("📋 Report Status"),
                html.P(str(report_data))
            ])
            
    except requests.RequestException as e:
        return html.Div([
            html.H3("❌ API Communication Error"),
            html.P(f"Failed to fetch data from API: {str(e)}")
        ])