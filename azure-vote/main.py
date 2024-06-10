from flask import Flask, request, render_template
import os
import random
import redis
import socket
import sys
import logging
from datetime import datetime

# App Insights
# TODO: Import required libraries for App Insights
from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.trace.samplers import ProbabilitySampler
from opencensus.trace.tracer import Tracer
from opencensus.ext.azure.metrics_exporter import new_metrics_exporter
from opencensus.ext.flask.flask_middleware import FlaskMiddleware

# Logging
logger = logging.getLogger(__name__)
logger.addHandler(AzureLogHandler(connection_string='InstrumentationKey=1ea6d0ce-1f8f-43ae-90e7-dd43e7281a9a'))
logger.setLevel(logging.INFO)

# Metrics
# TODO: Setup exporter
exporter = new_metrics_exporter(enable_standard_metrics=True, connection_string='InstrumentationKey=1ea6d0ce-1f8f-43ae-90e7-dd43e7281a9a')

# Tracing
# TODO: Setup tracer
tracer = Tracer(exporter=AzureExporter(connection_string='InstrumentationKey=1ea6d0ce-1f8f-43ae-90e7-dd43e7281a9a'),
                sampler=ProbabilitySampler(1.0))

app = Flask(__name__)

# Requests
# TODO: Setup flask middleware
middleware = FlaskMiddleware(app, exporter=AzureExporter(connection_string='InstrumentationKey=1ea6d0ce-1f8f-43ae-90e7-dd43e7281a9a'),
                             sampler=ProbabilitySampler(rate=1.0))

# Load configurations from environment or config file
app.config.from_pyfile('config_file.cfg')

if ("VOTE1VALUE" in os.environ and os.environ['VOTE1VALUE']):
    button1 = os.environ['VOTE1VALUE']
else:
    button1 = app.config['VOTE1VALUE']

if ("VOTE2VALUE" in os.environ and os.environ['VOTE2VALUE']):
    button2 = os.environ['VOTE2VALUE']
else:
    button2 = app.config['VOTE2VALUE']

if ("TITLE" in os.environ and os.environ['TITLE']):
    title = os.environ['TITLE']
else:
    title = app.config['TITLE']

# Redis Connection
r = redis.Redis()

# Change title to host name to demo NLB
if app.config['SHOWHOST'] == "true":
    title = socket.gethostname()

# Init Redis
if not r.get(button1): r.set(button1, 0)
if not r.get(button2): r.set(button2, 0)

@app.route('/', methods=['GET', 'POST'])
def index():
    print('>>>', request.method)
    if request.method == 'GET':
        # Get current values
        vote1 = r.get(button1).decode('utf-8')
        # TODO: use tracer object to trace cat vote
        with tracer.span(name="Cat vote") as cat_span:
            cat_span.add_attribute('cat_vote', vote1)
            cat_span.add_annotation('Cat vote is recorded')
        
        vote2 = r.get(button2).decode('utf-8')
        # TODO: use tracer object to trace dog vote
        with tracer.span(name="Dog vote") as dog_span:
            dog_span.add_attribute('dog_vote', vote2)

        # Return index with values
        return render_template("index.html", value1=int(vote1), value2=int(vote2), button1=button1, button2=button2, title=title)

    elif request.method == 'POST':
        if request.form['vote'] == 'reset':
            # Empty table and return results
            r.set(button1, 0)
            r.set(button2, 0)
            vote1 = r.get(button1).decode('utf-8')
            properties = {'custom_dimensions': {'Cats Vote': vote1}}
            # TODO: use logger object to log cat vote
            logger.info('Cat vote', extra=properties)

            vote2 = r.get(button2).decode('utf-8')
            properties = {'custom_dimensions': {'Dogs Vote': vote2}}
            # TODO: use logger object to log cat vote
            logger.info('Dog vote', extra=properties)

            return render_template("index.html", value1=int(vote1), value2=int(vote2), button1=button1, button2=button2, title=title)

        else:
            # Insert vote result into DB
            vote = request.form['vote']
            r.incr(vote, 1)

            # Get current values
            vote1 = r.get(button1).decode('utf-8')
            vote2 = r.get(button2).decode('utf-8')

            # Return results
            return render_template("index.html", value1=int(vote1), value2=int(vote2), button1=button1, button2=button2, title=title)

if __name__ == "__main__":
    # app.run(port=5001, debug=True)
    app.run(host='0.0.0.0', threaded=True, debug=True)  # remote
