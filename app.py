from flask import Flask, render_template, url_for, request, jsonify, redirect
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from user import User  # Import the User class from user.py
import mysql.connector
import bcrypt
import random

# Create MySQL database
database_config = {
    'host': 'localhost',
    'username': 'root',
    'password': '',
    'database': 'tournament_generator'
}

#flask initialization
app = Flask(__name__)
app.secret_key = 'VeryImportantSecret'  # Set a secret key for session security
login_manager = LoginManager()

#only allow authenticated users on the home page. 
#used flask!
@app.route('/')
@login_required
def home():
    # This view function will only be executed if the user is authenticated
    return render_template('home.html')

# Configure the login manager
@login_manager.unauthorized_handler
def unauthorized_callback():
    # Redirect unauthenticated users to the login page
    return redirect(url_for('login'))

# Initialize the login manager with the Flask app
login_manager.init_app(app)

#creates the user object using flask
@login_manager.user_loader
def load_user(username):
    conn = mysql.connector.connect(**database_config)
    # Create a cursor object to interact with the database
    cursor = conn.cursor()
    
    # Retrieve the user from the database based on the username
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user_data = cursor.fetchone()

    if user_data:
        # Create a User object using the retrieved data
        user = User(username=user_data[0], password=user_data[1])
        return user

    return None
    
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = mysql.connector.connect(**database_config)
        # Create a cursor object to interact with the database
        cursor = conn.cursor()
        
        # Check if the username exists in the database
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        
        if user:            
            stored_password = user[1]  # Assuming the password is stored in the third column
            
            # Verify the password
            if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
                # Password matches, login successful
                
                # Close the cursor and the database connection
                cursor.close()
                conn.close()
                
                #flask authentication user object
                user_object = load_user(username)
                
                # Login the user
                login_user(user_object)
                
                # Return a JSON response indicating login successful
                return jsonify({'message': 'Login successful'})
            
            # Return a JSON response indicating incorrect password
            return jsonify({'message': 'Incorrect password'})
        
        # If the username or password is incorrect, return an error message
        return jsonify({'message': 'Invalid username'})
    
    # If it's a GET request, render the login.html template
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm-password']
        
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        if password != confirm_password:
            return jsonify({'message': 'Passwords do not match!'})
        
        conn = mysql.connector.connect(**database_config)
        # Create a cursor object to interact with the database
        cursor = conn.cursor()

        # Check if the username already exists in the database
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        existing_user = cursor.fetchone()
        if existing_user:
            # Return a JSON response indicating that the username is already taken
            return jsonify({'message': 'Username already exists'})
        
        # Insert the user data into the database
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
        conn.commit()
        
        # Close the cursor and the database connection
        cursor.close()
        conn.close()
        
        #flask authentication user object
        user_object = load_user(username)
        
        # Login the user
        login_user(user_object)
        
        # Return a JSON response indicating success
        return jsonify({'message': 'Registration successful'})
    
    # If it's a GET request, render the register.html template
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

def getFixtures(combinations):
    fixtures = []
    for i in range(len(combinations)-1):
        for j in range(i+1, len(combinations)): 
            team1 = combinations[i]
            team2 = combinations[j]
            if team1[0] in team2 or team1[1] in team2:
                continue
            else:
                fixture = [team1[0]+" & "+team1[1], team2[0]+" & "+team2[1]]
                fixtures.append(fixture)
    return fixtures

def getFixtures1Player(combinations):
    fixtures = []
    for i in range(len(combinations)-1):
        for j in range(i+1, len(combinations)): 
            team1 = combinations[i]
            team2 = combinations[j]
            if team1[0] in team2:
                continue
            else:
                fixture = [team1[0], team2[0]]
                fixtures.append(fixture)
    return fixtures

def generate_fixtures(players, players_per_team, fixture_type):
    if players_per_team == 1:
        
        #home fixtures
        combinations = []
        for i in range(len(players)):
            team = [players[i]]
            combinations.append(team) 
        fixtures = getFixtures1Player(combinations)
        
        #away fixtures
        combinations = []
        if fixture_type == "home-away": #also do the away fixtures
            for i in range(len(players)-1, -1, -1):
                team = [players[i]]
                combinations.append(team) 
            away_fixtures = getFixtures1Player(combinations)
            fixtures.extend(away_fixtures) 
        return fixtures
    
    elif players_per_team == 2:
        
        #home fixtures
        combinations = []
        for i in range(len(players)-1): 
            for j in range(i+1, len(players)):
                team = [players[i], players[j]]
                combinations.append(team) 
        fixtures = getFixtures(combinations)
        
        #away fixtures
        combinations = []
        if fixture_type == "home-away": #also do the away fixtures
            for i in range(len(players)-1, 0, -1):
                for j in range(i-1, -1, -1):
                    team = [players[i], players[j]]
                    combinations.append(team) 
            away_fixtures = getFixtures(combinations)
            fixtures.extend(away_fixtures)        
        return fixtures
    
def isSortedFixture(min_players, home_team_players, away_team_players):
    #check if all keys in min_players are either in home_team_players or away_team_players
    all_present = all(key in home_team_players or key in away_team_players for key in min_players)

    if all_present:
        return True
    else:
        return False

@app.route('/submit-tournament', methods=['POST'])
def submit_tournament():
    # Retrieve the form data from the request
    tournament_name = request.form.get('tournament-name')
    player_names = request.form.get('player-names')
    players_per_team = request.form.get('players-per-team')
    fixture_type = request.form.get('fixture-type')
    
    #convert players to the int format
    if players_per_team == "one-player":
        players_per_team = 1
    elif players_per_team == "two-players":
        players_per_team = 2
    
    #validate the player_names input
    player_names_clean = []
    player_names_list = player_names.split(",")
    for name in player_names_list:
        clean_name = name.strip()
        if clean_name != "":
            if clean_name in player_names_clean:
                return jsonify({'message': "Please enter unique players"})
            player_names_clean.append(clean_name)
            
    if len(player_names_clean) < 2:
        message = "Please enter at least two players!"
        # Return a JSON response to the client
        return jsonify({'message': message})
    
    if players_per_team == 2 and len(player_names_clean) < 4:
        message = "Please enter at least 4 players for the two-player game!"
        # Return a JSON response to the client
        return jsonify({'message': message})
    
    #for db storing
    clean_names = ','.join(player_names_clean)
    
    if tournament_name.isspace():
        return jsonify({'message': "Please enter a valid Tournament Name"})
    
    #database 
    conn = mysql.connector.connect(**database_config)
    # Create a cursor object to interact with the database
    cursor = conn.cursor()
    
    message = "Failed to add to DB"
    
    # Insert a new entry into the tournament_id table
    insert_query = "INSERT INTO tournament_details (tournament_name, username, player_names, players_per_team, fixture_type) VALUES (%s, %s, %s, %s, %s)"
    values = (tournament_name, current_user.username, clean_names, players_per_team, fixture_type)

    try:
        #insert into tournament_details
        cursor.execute(insert_query, values)
        conn.commit()
        message = "Tournament submitted successfully"
        
        #insert into results table
        fixtures = generate_fixtures(player_names_clean, players_per_team, fixture_type)
    
        # Shuffle the elements in the entire list
        random.shuffle(fixtures)
        
        if players_per_team*2 < len(player_names_clean): #check if players must wait
            print("Some players will wait and we have already sorted!")
            
            #initialize the number of games each player played
            player_played = {player: 0 for player in player_names_clean} 
            
            # Get the players with the minimum games played
            # players_per_team*2 is the number of players playing
            min_players = sorted(player_played, key=lambda k: player_played[k])[:players_per_team*2]

            fixture_index = 0
            ordered_fixtures = [] #final list of fixtures
            while len(fixtures) !=0: #no more fixtures left
                fixture = fixtures[fixture_index]
                home_team = fixture[0]
                away_team = fixture[1]
                home_team_players = home_team.split(" & ")
                away_team_players = away_team.split(" & ")
                
                #if found a fixture with least waiting time 
                if isSortedFixture(min_players, home_team_players, away_team_players) == True:
                    
                    ordered_fixtures.append(fixture)
                    fixtures.remove(fixture)
                    fixture_index = 0
                    less_player = 1
                    
                    #increment playing players by 1
                    for player in home_team_players:
                        player_played[player]+=1
                    for player in away_team_players:
                        player_played[player]+=1
                        
                    # Get all the players playing with the minimum values
                    min_players = sorted(player_played, key=lambda k: player_played[k])[:players_per_team*2]
                
                else: # fixture found not with least waiting time 
                    fixture_index = fixture_index+1 #go to next fixture
                    
                    #if gone through entire fixture list and no fixture suits the minimum waiting time
                    if fixture_index == len(fixtures): 
                        fixture_index = 0 #reset if out of range
                        
                        #Decrease the keys with the minimum values by 1
                        min_players = sorted(player_played, key=lambda k: player_played[k])[:players_per_team*2-less_player]
                        less_player+=1
        else:
            ordered_fixtures = fixtures
            print("No player needs to wait!")
        
        # for i in ordered_fixtures:
        #     print(i)
            
        # Retrieve the generated id using the column values
        select_query = "SELECT id FROM tournament_details WHERE tournament_name = %s AND username = %s"
        select_values = (tournament_name, current_user.username)

        cursor.execute(select_query, select_values)
        tournament_id = cursor.fetchone()[0]
        # print("Generated id:", tournament_id)

        # Iterate over the ordered_fixtures list and insert each fixture into the results table
        for fixture in ordered_fixtures:
            home_team = fixture[0]
            away_team = fixture[1]

            # Prepare the INSERT query
            insert_query = "INSERT INTO results (home_team, away_team, tournament_id) VALUES (%s, %s, %s)"
            values = (home_team, away_team, tournament_id)

            # Execute the INSERT query
            cursor.execute(insert_query, values)
        
        conn.commit()

    except mysql.connector.Error as error:
        message =  "Tournament name already exists for this user"

    # Close the cursor and connection
    cursor.close()
    conn.close()
    
    # Return a JSON response to the client
    return jsonify({'message': message})

def get_tournaments(username):
    #database 
    conn = mysql.connector.connect(**database_config)
    # Create a cursor object to interact with the database
    cursor = conn.cursor()
    
    cursor.execute("SELECT tournament_name FROM tournament_details WHERE username = %s", (username,))
    tournament_names = [row[0] for row in cursor.fetchall()] #row is only column tournament_name!
    
    # Close the cursor and the database connection
    cursor.close()
    conn.close()
    
    return tournament_names

@app.route('/select_tournament_fixtures')
@login_required
def select_tournament_fixtures():
    # This view function will only be executed if the user is authenticated

    # Retrieve the tournaments from the database or any other data source
    tournaments = get_tournaments(current_user.username)

    # Render the select_tournament_fixtures.html template with the tournaments data
    return render_template('select_tournament_fixtures.html', tournaments=tournaments)

@app.route('/tournament/<tournament_name>')
@login_required
def tournament(tournament_name):
    # print(tournament_name, current_user.username)
    # Retrieve the tournament data from the database based on the tournament_name
    conn = mysql.connector.connect(**database_config)
    # Create a cursor object to interact with the database
    cursor = conn.cursor()

    # Prepare the SELECT query
    select_query = "SELECT id FROM tournament_details WHERE tournament_name = %s AND username = %s"
    values = (tournament_name, current_user.username)

    # Execute the SELECT query
    cursor.execute(select_query, values)

    # Fetch the result
    result = cursor.fetchone()

    if result:
        id = result[0]
        # Prepare the SELECT query
        select_query = "SELECT * FROM results WHERE tournament_id = %s"
        values = (id,)

        # Execute the SELECT query
        cursor.execute(select_query, values)

        # Fetch all the rows
        rows = cursor.fetchall()
        # print(rows)
    else:
        print("Tournament not found")

    # Close the cursor and the database connection
    cursor.close()
    conn.close()

    # Render the tournament page template and pass the tournament data
    return render_template('fixtures_results.html', results=rows, tournament_name=tournament_name)

@app.route('/update_scores', methods=['POST'])
def update_scores():
    fixture_index = int(request.form.get('fixtureIndex'))
    home_score = request.form.get('homeScore')
    away_score = request.form.get('awayScore')
    id = request.form.get('id')
    print("Fixture:", fixture_index, home_score,":", away_score, "id:", id)
    
    # Prepare the INSERT query
    conn = mysql.connector.connect(**database_config)
    # Create a cursor object to interact with the database
    cursor = conn.cursor()
    query = """
    UPDATE results
    SET home_score = %s, away_score = %s
    WHERE (tournament_id, (
        SELECT id
        FROM results
        WHERE tournament_id = %s
        ORDER BY id
        LIMIT 1 OFFSET %s
    )) = (%s, id)"""
    # Execute the query
    cursor.execute(query, (home_score, away_score, id, fixture_index - 1, id))

    conn.commit()
    
    # Close the cursor and the database connection
    cursor.close()
    conn.close()
    
    # Return a JSON response if required
    return jsonify(success=True)


#table
@app.route('/select_tournament_table')
@login_required
def select_tournament_table():
    # This view function will only be executed if the user is authenticated

    # Retrieve the tournaments from the database or any other data source
    tournaments = get_tournaments(current_user.username)

    # Render the select_tournament_table.html template with the tournaments data
    return render_template('select_tournament_table.html', tournaments=tournaments)

def getTable(rows):
    # rows = [
    # (47, 'Shlomo & Moshe', '2', '0', 'Yaakov & Shmuli', 170),
    # (48, 'Shlomo & Yaakov', '2', '3', 'Moshe & Shmuli', 170),
    # (49, 'Shlomo & Shmuli', '2', '5', 'Moshe & Yaakov', 170)
    # ]

    # Dictionary to store each player's statistics
    player_stats = {}

    # Calculate player statistics
    for row in rows:
        _, home_team, home_score, away_score, away_team, _ = row

        #split for individual players
        home_players = home_team.split(' & ')
        away_players = away_team.split(' & ')
        
        #initialze players with 0 points...
        for player in home_players:
            if player not in player_stats:
                player_stats[player] = {
                    'matches_played': 0,
                    'wins': 0,
                    'draws': 0,
                    'losses': 0,
                    'goals_for': 0,
                    'goals_against': 0,
                    'goal_difference': 0,
                    'points': 0
                }
        for player in away_players:
            if player not in player_stats:
                player_stats[player] = {
                    'matches_played': 0,
                    'wins': 0,
                    'draws': 0,
                    'losses': 0,
                    'goals_for': 0,
                    'goals_against': 0,
                    'goal_difference': 0,
                    'points': 0
                }
                
        #the match is not played yet or incomplete
        if home_score.isdigit() == False or away_score.isdigit() == False:
            continue
        
        home_goals = int(home_score)
        away_goals = int(away_score)

        #update the points for the matches for each player
        for player in home_players:
            player_stats[player]['matches_played'] += 1
            player_stats[player]['goals_for'] += home_goals
            player_stats[player]['goals_against'] += away_goals
            player_stats[player]['goal_difference'] = player_stats[player]['goals_for']-player_stats[player]['goals_against']

            if home_goals > away_goals:
                player_stats[player]['wins'] += 1
                player_stats[player]['points'] += 3
            elif home_goals == away_goals:
                player_stats[player]['draws'] += 1
                player_stats[player]['points'] += 1
            else:
                player_stats[player]['losses'] += 1

        for player in away_players:
            player_stats[player]['matches_played'] += 1
            player_stats[player]['goals_for'] += away_goals
            player_stats[player]['goals_against'] += home_goals
            player_stats[player]['goal_difference'] = player_stats[player]['goals_for']-player_stats[player]['goals_against']

            if away_goals > home_goals:
                player_stats[player]['wins'] += 1
                player_stats[player]['points'] += 3
            elif away_goals == home_goals:
                player_stats[player]['draws'] += 1
                player_stats[player]['points'] += 1
            else:
                player_stats[player]['losses'] += 1

    # Sort players based on points, goal difference, and goals scored
    sorted_players = sorted(
        player_stats.items(),
        key=lambda x: (x[1]['points'], x[1]['goal_difference'], x[1]['goals_for']),
        reverse=True
    )

    # Generate the table
    table_rows = []
    # print("Pos\tTeam\tMP\tW\tD\tL\tGF\tGA\tGD\tPts")
    for i, (player, stats) in enumerate(sorted_players):
        # pos = i + 1
        # team = player
        # mp = stats['matches_played']
        # wins = stats['wins']
        # draws = stats['draws']
        # losses = stats['losses']
        # gf = stats['goals_for']
        # ga = stats['goals_against']
        # gd = gf - ga
        # pts = stats['points']
        
        row = {
            'Pos': i + 1,
            'Team': player,
            'MP': stats['matches_played'],
            'W': stats['wins'],
            'D': stats['draws'],
            'L': stats['losses'],
            'GF': stats['goals_for'],
            'GA': stats['goals_against'],
            'GD': stats['goal_difference'],
            'Pts': stats['points']
        }
        table_rows.append(row)
    return table_rows

        # print(f"{pos}\t{team}\t{mp}\t{wins}\t{draws}\t{losses}\t{gf}\t{ga}\t{gd}\t{pts}")


@app.route('/tournament_table/<tournament_name>')
@login_required
def tournament_table(tournament_name):
    # print(tournament_name, current_user.username)
    # Retrieve the tournament data from the database based on the tournament_name
    conn = mysql.connector.connect(**database_config)
    # Create a cursor object to interact with the database
    cursor = conn.cursor()

    # Prepare the SELECT query
    select_query = "SELECT id FROM tournament_details WHERE tournament_name = %s AND username = %s"
    values = (tournament_name, current_user.username)

    # Execute the SELECT query
    cursor.execute(select_query, values)

    # Fetch the result
    result = cursor.fetchone()

    if result:
        id = result[0]
        # Prepare the SELECT query
        select_query = "SELECT * FROM results WHERE tournament_id = %s"
        values = (id,)

        # Execute the SELECT query
        cursor.execute(select_query, values)

        # Fetch all the rows
        rows = cursor.fetchall()
        table_rows = getTable(rows)
        print(table_rows)
    else:
        print("Tournament not found")

    # Close the cursor and the database connection
    cursor.close()
    conn.close()

    # Render the tournament page template and pass the tournament data
    return render_template('table.html', table_rows=table_rows, tournament_name=tournament_name)

if __name__ == '__main__':
    app.run(debug=True)