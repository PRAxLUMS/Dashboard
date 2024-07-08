import dash
from dash import dcc, html
import dash.dependencies as dd
import pandas as pd
import pyarrow
import fastparquet
import plotly.graph_objects as go

# Define the file path for the preprocessed Parquet file
parquet_file_path = "data/Filtered_Restaurants.parquet"

# Load and preprocess the dataset
df = pd.read_parquet(parquet_file_path)
df['earliest_known_date'] = pd.to_datetime(df['earliest_known_date'], errors='coerce')

cutoff_date = pd.to_datetime("2023-11-01")
before_cutoff = df[df['earliest_known_date'] < cutoff_date]
after_cutoff = df[df['earliest_known_date'] >= cutoff_date]

# Compliance level colors
compliance_colors = {
    -999: 'gray', 0: 'black', 1: 'red', 2: 'blue', 3: 'yellow', 4: 'orange', 5: 'green'
}

# Function to generate compliance level labels with counts
def generate_compliance_labels(data):
    compliance_counts = data['Compliance Level'].value_counts().to_dict()
    return {
        -999: f"Registered but sales tax data NA ({compliance_counts.get(-999, 0)})",
        0: f"Unregistered ({compliance_counts.get(0, 0)})",
        1: f"Registered but not filed ({compliance_counts.get(1, 0)})",
        2: f"Filed 0 at least 1 month ({compliance_counts.get(2, 0)})",
        3: f"Filed positively at least 1 month but paid 0 ({compliance_counts.get(3, 0)})",
        4: f"Filed & paid positively at least 1 month ({compliance_counts.get(4, 0)})",
        5: f"Filed & paid positively all months ({compliance_counts.get(5, 0)})"
    }

# Define Dash application
app = dash.Dash(__name__)
app.config.suppress_callback_exceptions = True
app.config.prevent_initial_callbacks = True

app.layout = html.Div([
    dcc.RadioItems(
        id='page-selector',
        options=[
            {'label': 'Home', 'value': 'home'},
            {'label': 'Before 1-11-2023', 'value': 'before'},
            {'label': 'After 1-11-2023', 'value': 'after'}
        ],
        value='home',
        labelStyle={'display': 'inline-block'}
    ),
    html.Div(id='page-content', children=[
        html.Div([
            html.H1("Welcome to the Restaurant Tax Compliance Dashboard"),
            html.P("This dashboard allows you to explore the tax compliance status of restaurants in Lahore. "
                   "Use the radio buttons above to navigate to the specific pages showing restaurants before and after November 1, 2023.")
        ])
    ])
])

# Callback to update the page content based on the selection
@app.callback(
    dd.Output('page-content', 'children'),
    [dd.Input('page-selector', 'value')]
)
def render_page_content(page):
    if page == 'home':
        return html.Div([
            html.H1("Welcome to the Restaurant Tax Compliance Dashboard"),
            html.P("This dashboard allows you to explore the tax compliance status of restaurants in Lahore. "
                   "Use the radio buttons above to navigate to the specific pages showing restaurants before and after November 1, 2023.")
        ])
    elif page in ['before', 'after']:
        data_to_show = before_cutoff if page == 'before' else after_cutoff
        compliance_labels = generate_compliance_labels(data_to_show)

        # Create layers for different compliance levels
        fig = go.Figure()

        for level, color in compliance_colors.items():
            filtered_data = data_to_show[data_to_show['Compliance Level'] == level]
            fig.add_trace(go.Scattermapbox(
                lat=filtered_data['latitude_combined'],
                lon=filtered_data['longitude_combined'],
                mode='markers',
                marker=dict(size=5, color=color),
                name=compliance_labels[level],
                customdata=filtered_data.to_dict('records'),  # Attach all data for the customdata field
                hoverinfo='none'
            ))

        # Update the layout of the map
        fig.update_layout(
            mapbox=dict(
                center=dict(lat=data_to_show['latitude_combined'].mean(), lon=data_to_show['longitude_combined'].mean()),
                zoom=10,
                style="carto-positron"
            ),
            margin={"r":0,"t":0,"l":0,"b":0},
            legend=dict(
                title="Compliance Levels",
                itemsizing="constant",
                itemclick="toggle",
                itemdoubleclick="toggleothers",
                font=dict(size=10),
                itemwidth=30,
                orientation="v",
                x=1,
                xanchor="right",
                y=1,
                yanchor="top"
            )
        )

        return html.Div([
            dcc.Graph(id='map', figure=fig, config={'displayModeBar': False}, style={'width': '100%', 'height': '60vh', 'display': 'inline-block'}),
            html.Div(id='restaurant-details', style={'width': '100%', 'height': '40vh', 'padding': '10px', 'border': '1px solid #ccc', 'overflow-y': 'scroll'})
        ])

# Callback to display restaurant details on marker click
@app.callback(
    dd.Output('restaurant-details', 'children'),
    [dd.Input('map', 'clickData')]
)
def display_restaurant_details(clickData):
    if clickData is None:
        return "Click on a marker to see restaurant details here."

    restaurant = clickData['points'][0]['customdata']

    return html.Div(
        [
            html.H4("Restaurant Details"),
            html.Div([html.Span("ID: ", style={'font-weight': 'bold'}), restaurant['ID']]),
            html.Div([html.Span("Foodpanda: ", style={'font-weight': 'bold'}), html.A("Link", href=restaurant['LinkFP'], target="_blank")]),
            html.Div([html.Span("Facebook: ", style={'font-weight': 'bold'}), html.A("Link", href=restaurant['LinkFB'], target="_blank")]),
            html.Div([html.Span("Google Maps: ", style={'font-weight': 'bold'}), html.A("Link", href=restaurant['LinkGM'], target="_blank")]),
            html.Div([html.Span("Comp No: ", style={'font-weight': 'bold'}), restaurant['COMPUTER_NO']]),
            html.Div([html.Span("Restaurant Type: ", style={'font-weight': 'bold'}), restaurant['restaurant_type']]),
            html.Div([html.Span("DateScrapedFP: ", style={'font-weight': 'bold'}), restaurant['DateScrapedFP']]),
            html.Div([html.Span("DateScrapedGM: ", style={'font-weight': 'bold'}), restaurant['DateScrapedGM']]),
            html.Div([html.Span("DateScrapedFB: ", style={'font-weight': 'bold'}), restaurant['DateScrapedFB']]),
            html.Div([html.Span("CreationDateFB: ", style={'font-weight': 'bold'}), restaurant['CreationDateFB']]),
            html.Div([html.Span("Reg Date: ", style={'font-weight': 'bold'}), restaurant['REGISTRATION_DATE']]),
            html.Div([html.Span("Interview Date: ", style={'font-weight': 'bold'}), restaurant['interview_date']]),
            html.Div([html.Span("Lat: ", style={'font-weight': 'bold'}), restaurant['latitude_combined']]),
            html.Div([html.Span("Lon: ", style={'font-weight': 'bold'}), restaurant['longitude_combined']]),
            html.Div([html.Span("Compliance Level: ", style={'font-weight': 'bold'}), restaurant['Compliance Level']]),
            html.Div([html.Span("Filed Months: ", style={'font-weight': 'bold'}), restaurant['Filed Months Count']]),
            html.Div([html.Span("Earliest Known Date: ", style={'font-weight': 'bold'}), restaurant['earliest_known_date']]),
            html.Div([html.Span("Name: ", style={'font-weight': 'bold'}), restaurant['Display Name']])
        ],
        style={'display': 'inline-block'}
    )

if __name__ == '__main__':
    app.run_server(debug=True)
