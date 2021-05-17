
from server_config import BOKEH_URL, WIK_URL
from flask import Flask, render_template, render_template_string, request, redirect, session
from user_config import valid_user, valid_password
from bokeh.embed import server_session
from bokeh.util.token import generate_session_id
from gevent.pywsgi import WSGIServer
from gevent import monkey
from pathlib import Path
# need to patch sockets to make requests async
monkey.patch_all()

TEMPLATE_FOLDER = Path(__file__).parent.joinpath('../templates').resolve()
app = Flask(__name__,
            template_folder='../templates',
            static_folder='../static')
app.config['SECRET_KEY'] = 'supersecret'

# write app.html
app_template = TEMPLATE_FOLDER.joinpath("app.html")

if app_template.exists():
    app_template.unlink()

app_template.write_text(
    f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="X-UA-Compatible" content="ie=edge">    
        <link rel="stylesheet" href="{{{{url_for('static',filename='css/plot_style.css')}}}}"> 
        <script type="text/javascript" src={{{{cdn_js | safe}}}}></script>
        <title>Bokeh Plot</title>
    </head>
    
    <body>
    {{{{script1 | safe}}}}
    <form class="right" action="{WIK_URL}/logout" method="POST">
        <button type="submit" style="float: left;"> 
        <img src="static\icons\PNGIX.com_logout-button-png_3396763.png" height="20"/>
    </form>
    </body>
    </html>""")

app.debug = True
@app.route("/login", methods=['POST', 'GET'])
def login():
    """App route to login page."""
    
    if request.method == "POST":
        user_name = request.form.get("uname")
        user_pswrd = request.form.get("upassword")
        if valid_user(user_name) and valid_password(user_pswrd):
            session['auth'] = 1
            return redirect(f'{WIK_URL}/wik')
        else:
            session['auth'] = 0
    elif session.get('auth'):
         return redirect(f'{WIK_URL}/wik')
        
    return render_template("login.html")


 # pull a new session from a running Bokeh server

@app.route('/wik')
def wik():
    """App route for wik application."""
    if 'auth' in session.keys():
        if session['auth'] == 1:
            script1 = server_session(
            url=f'{BOKEH_URL}', 
            session_id=generate_session_id())

            return render_template("app.html",
                                    script1=script1,
                                    relative_urls=True)

    return redirect(f"{WIK_URL}/login")


@app.route('/logout', methods=['POST', 'GET'])
def logout():
    """App route to logout page."""
    session['auth'] = 0
    return redirect(f'{WIK_URL}/login')


if __name__ == "__main__":
 #    app.run(debug=True)
     app = WSGIServer(('127.0.0.1', 5000), app.wsgi_app)
     app.serve_forever()