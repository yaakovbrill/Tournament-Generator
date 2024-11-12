# Tournament Generator

## Introduction

The Tournament Generator is a web tool designed to help manage and track soccer FIFA tournaments. Whether you're hosting a small friendly competition or a larger event, this platform provides an easy and efficient way to set up and track your tournament.

## Overview

Visit [Tournament Generator](https://tournament.pythonanywhere.com/), register, and navigate to "Create Tournament". Enter player names, select team sizes (1 or 2 players), and the platform will generate fixtures. Points are tracked automatically. This tool is aimed at organizing and managing soccer FIFA tournaments.

## Features
- **Easy Setup**: Quickly create tournaments with customizable settings. Enter player names separated by commas, tournament name, team size (1 or 2 players), and fixture type (One Fixture or Home and Away).
- **Match Management**: Randomly generate matches and team assignments.
- **Score Tracking**: Real-time score tracking.
- **Winner Determination**: Points are tallied based on tournament rules (3 points for a win, 1 for a draw, 0 for a loss) into the traditional soccer scoring table system.

This tool was created with Python, SQL, Flask, JavaScript, HTML, and CSS, and it is hosted on PythonAnywhere. It utilizes both GET and POST API methods with Flask’s @app.route for handling requests.

To run this project locally, you can clone the repository and use XAMPP to set up a local server. Simply start XAMPP and then execute python app.py to launch the application.