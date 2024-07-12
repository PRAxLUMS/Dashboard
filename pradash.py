import dash
from dash import dcc, html
import dash.dependencies as dd
import pandas as pd
import plotly.graph_objects as go

# Define the file path for the preprocessed Parquet file
parquet_file_path = "D:\\Dropbox\\PRA\\Output\\_10_Timestamped Maps\\Updated_Filtered_Restaurants.parquet"

# Load and preprocess the dataset
df = pd.read_parquet(parquet_file_path)
df['earliest_known_date'] = pd.to_datetime(df['earliest_known_date'], errors='coerce')

cutoff_date = pd.to_datetime("2023-11-01")

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
            {'label': 'After 1-11-2023', 'value': 'after'},
            {'label': 'Simplified Compliance Before 1-11-2023', 'value': 'simplified_before'},
            {'label': 'Simplified Compliance After 1-11-2023', 'value': 'simplified_after'}
        ],
        value='home',
        labelStyle={'display': 'inline-block'}
    ),
    html.Div(id='page-content', children=html.Div([
        html.H1("Welcome to the Restaurant Tax Compliance Dashboard"),
        html.P("Use the radio buttons above to navigate through different pages."),
        html.P([
            "Link to access dataset: ",
            dcc.Link("Dataset", href="https://www.dropbox.com/scl/fi/v88fbazk5ob14fi5zo8tb/Updated_Filtered_Restaurants.xlsx?rlkey=oqwi5xyzl131zg69cr4kxsciy&dl=0")
        ])
    ]))
])

@app.callback(
    dd.Output('page-content', 'children'),
    [dd.Input('page-selector', 'value')]
)
def render_page_content(page):
    if page == 'home':
        return html.Div([
            html.H1("Welcome to the Restaurant Tax Compliance Dashboard"),
            html.P("Use the radio buttons above to navigate through different pages."),
            html.P([
                "Link to access dataset: ",
                dcc.Link("Dataset", href="https://www.dropbox.com/scl/fi/96xj7ggkjcyqmu79s1btk/Updated_Filtered_Restaurants.parquet?rlkey=jeiq7o5buzqsnvplnbu1qjdh7&dl=0")
            ])
        ])

    data_to_show = df[df['earliest_known_date'] < cutoff_date] if 'before' in page else df[df['earliest_known_date'] >= cutoff_date]
    compliance_field = 'Compliance Level' if 'simplified' not in page else 'Simplified Compliance Level'
    compliance_colors = {-999: 'gray', 0: 'black', 1: 'red', 2: 'green'} if 'simplified' in page else {-999: 'gray', 0: 'black', 1: 'red', 2: 'blue', 3: 'yellow', 4: 'orange', 5: 'green'}
    compliance_labels = {-999: 'Registered but data NA', 0: 'Unregistered', 1: 'Filed 0 at least 1 month', 2: 'Paid > 0 at least 1 month'} if 'simplified' in page else {-999: 'Registered but data NA', 0: 'Unregistered', 1: 'Registered but not filed', 2: 'Filed 0 at least 1 month', 3: 'Filed > 0 at least 1 month but paid 0', 4: 'Filed & paid > 0 at least 1 month', 5: 'Filed & paid positively all months'}
    compliance_labels = {level: f"{label} ({data_to_show[compliance_field].value_counts().get(level, 0)})" for level, label in compliance_labels.items()}

    fig = go.Figure()
    for level, color in compliance_colors.items():
        filtered_data = data_to_show[data_to_show[compliance_field] == level]
        marker_size = 3 if level == 0 else 5  # Smaller and more transparent for level 0
        fig.add_trace(go.Scattermapbox(
            lat=filtered_data['latitude_combined'],
            lon=filtered_data['longitude_combined'],
            mode='markers',
            marker=dict(size=marker_size, color=color),
            name=compliance_labels[level],
            customdata=filtered_data.to_dict('records'),
            hoverinfo='text',
            text=filtered_data['Display Name']
        ))

    fig.update_layout(
        mapbox=dict(
            center=dict(lat=data_to_show['latitude_combined'].mean(), lon=data_to_show['longitude_combined'].mean()),
            zoom=10,
            style="open-street-map"
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
    return html.Div([
        html.H4("Restaurant Details"),
        html.Div([html.Span("Name: ", style={'font-weight': 'bold'}), restaurant['Display Name']]),
        html.Div([html.Span("ID: ", style={'font-weight': 'bold'}), restaurant['ID']]),
        html.Div([html.Span("Foodpanda: ", style={'font-weight': 'bold'}), html.A("Link", href=restaurant['LinkFP'], target="_blank")]),
        html.Div([html.Span("Google Maps: ", style={'font-weight': 'bold'}), html.A("Link", href=restaurant['LinkGM'], target="_blank")]),
        html.Div([html.Span("Facebook: ", style={'font-weight': 'bold'}), html.A("Link", href=restaurant['LinkFB'], target="_blank")]),
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
        html.Div([html.Span("Simplified Compliance Level: ", style={'font-weight': 'bold'}), restaurant['Simplified Compliance Level']]),
        html.Div([html.Span("Filed Months (1.11.22 - 31.10.23): ", style={'font-weight': 'bold'}), restaurant['Filed Months Count/12']]),
        html.Div([html.Span("Earliest Known Date: ", style={'font-weight': 'bold'}), restaurant['earliest_known_date']])
    ], style={'display': 'inline-block'})

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8000)