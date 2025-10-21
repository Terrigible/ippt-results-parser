from base64 import b64decode
from io import BytesIO, StringIO

import dash_bootstrap_components as dbc
import pandas as pd
import polars as pl
from dash import Dash, Input, Output, State, dcc, html, no_update

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], compress=True)

server = app.server

app.layout = html.Div(
    [
        html.H1("IPPT NR Generator"),
        html.Label(children='NR (Excel file with column headers that include "NRIC")'),
        dcc.Upload(
            id="nr-upload",
            children="Drag and drop or click to select files",
            style={
                "height": "60px",
                "lineHeight": "60px",
                "borderWidth": "1px",
                "borderStyle": "dashed",
                "borderRadius": "5px",
                "textAlign": "center",
            },
        ),
        html.P(),
        html.Label(children="Result XML File"),
        dcc.Upload(
            id="results-upload",
            children="Drag and drop or click to select files",
            style={
                "height": "60px",
                "lineHeight": "60px",
                "borderWidth": "1px",
                "borderStyle": "dashed",
                "borderRadius": "5px",
                "textAlign": "center",
            },
        ),
        html.P(),
        html.Label("Filename"),
        html.Br(),
        dcc.Input(id="filename-input", type="text", placeholder="results"),
        html.Div(".xlsx", style={"display": "inline-block"}),
        html.P(),
        html.Button(
            id="download-button", children="Download", style={"margin": "auto"}
        ),
        dcc.Download(id="download"),
    ],
    style={"maxWidth": "500px", "margin": "auto"},
)


@app.callback(
    Output("nr-upload", "children"),
    Input("nr-upload", "filename"),
    prevent_initial_call=True,
)
def update_nr_upload(filename: str):
    return f"Uploaded {filename}"


@app.callback(
    Output("results-upload", "children"),
    Input("results-upload", "filename"),
    prevent_initial_call=True,
)
def update_results_upload(filename: str):
    return f"Uploaded {filename}"


@app.callback(
    Output("download", "data"),
    Input("download-button", "n_clicks"),
    State("nr-upload", "contents"),
    State("results-upload", "contents"),
    State("filename-input", "value"),
    prevent_initial_call=True,
)
def update_graph(_, nr_upload: str, results_upload: str, filename: str):
    if nr_upload is None or results_upload is None:
        return no_update
    nr_type, nr_content = nr_upload.split(",")
    results_type, results_content = results_upload.split(",")
    ippt = pl.from_pandas(
        pd.read_xml(
            BytesIO(b64decode(results_content)),
            xpath="record",
            dtype={"fifth_station_scr": str},
        )
    ).select(
        "nric",
        "sit_up_scr",
        "sit_up_pt",
        "chin_up_scr",
        "chin_up_pt",
        "fifth_station_scr",
        "fifth_station_pt",
        "total_pt",
        "overall_result",
        "award_ind",
    )

    ippt = ippt.with_columns(
        pl.col("fifth_station_scr").str.replace(r"\.", ":"),
        pl.when(pl.col("award_ind") == "N")
        .then("overall_result")
        .otherwise(
            pl.concat_str(
                pl.col("overall_result"), pl.lit("("), pl.col("award_ind"), pl.lit(")")
            )
        )
        .alias("award_ind"),
    ).drop("overall_result")
    ippt = ippt.rename(
        {
            "nric": "NRIC",
            "sit_up_scr": "Sit Up Reps",
            "sit_up_pt": "Sit Up Pts",
            "chin_up_scr": "Push Up Rep",
            "chin_up_pt": "Push Up Pts",
            "fifth_station_scr": "2.4 Time",
            "fifth_station_pt": "2.4 Pts",
            "total_pt": "Total Pts",
            "award_ind": "Result",
        },
    )
    nr = pl.read_excel(BytesIO(b64decode(nr_content)))
    df = nr.join(ippt, on="NRIC", how="left").drop("NRIC")

    with BytesIO() as output_bytes:
        df.write_excel(output_bytes, column_formats={"4D": "0"})
        output_bytes.seek(0)

        return dcc.send_bytes(
            output_bytes.read(),
            f"{filename or 'results'}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            index=False,
        )


if __name__ == "__main__":
    app.run(debug=True)
