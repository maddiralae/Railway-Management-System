from flask import Flask, render_template, redirect, url_for, request, session, flash, g
from functools import wraps
import sqlite3
import pandas as pd
app = Flask(__name__)

app.secret_key = "qwertyuiopasdfghjklzxcvbnm"
app.database =  "projectDB.db"

trains=[]
distance={}
data=[]
trip_date = ''
src = 'null'
dst = 'null'
train_id = ''
class_id = ''
seats = [0,0,0,0]
names = []
ages = []
tot_dist=0
departure = ''
arrival = ''
fare = 0
seat_no = 0
seat_nos = []


#login required decorator
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('You Need To Login First')
            return redirect(url_for('login'))
    return wrap

@app.route("/", methods=['GET', 'POST'])
def default():
    session.pop('logged_in', None)
    return render_template("index.html")

# route for handling the signup page session
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        name = request.form['name']
        email = request.form['email']
        contact = request.form['phone']
        password = request.form['password']
         
        g.db = connect_db()
        cur = g.db.execute("insert into User(usrname,name,password,email,contact) VALUES (?,?,?,?,?)",(username,name,password,email,contact) )
        g.db.commit()
        g.db.close()

        session['logged_in'] = True
        flash('Sign Up Successful !!! Hurray.....')
        return redirect(url_for('user1'))            
    return render_template('signup.html', error=error)

# route for handling the login page session
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        usrname = request.form['username']
        passwd = request.form['password']
        g.db = connect_db()
        
        df=pd.read_sql_query("select usrname,password from User",g.db)
        count=df.shape[0]
        flag=0
        for i in range(count):
            if (usrname==df.ix[:,'usrname'][i]):
                flag=1
                break
        if(flag==0):
            error = 'Invalid Credentials. Please try again.'
            
        else:
            password=df.ix[:,'password'][i]
            if(passwd==password):
                session['logged_in'] = True
                flash('You Are Logged In')
                return redirect(url_for('user1'))

            else:
                error = 'Invalid Credentials. Please try again.'

    return render_template('login.html', error=error)

#user1 page contents
@app.route("/user1", methods=['GET', 'POST'])
@login_required
def user1():        
    
    if request.method == 'POST':
        global src 
        src = request.form['source']
        global dst 
        dst = request.form['destination']
        global trip_date
        trip_date = request.form['date']
        global distance

        g.db = connect_db()
        trains=[]
        distance={}
        data=[]
        def find_trains(source,dest):
            global distance
            s_trains=[16592,11304,12604,12008,16524]

            for train in s_trains :
                col_name = "s_" + str(train)
                df1 = pd.read_sql_query("SELECT station,"+col_name+" from Route where "+col_name+"!='' and station='" + source+"';",g.db)
                df2 = pd.read_sql_query("SELECT station,"+col_name+" from Route where "+col_name+"!='' and station='" + dest+"';",g.db)
                if(df1.empty or df2.empty):
                    continue
                frames=[df1,df2]
                df=pd.concat(frames)
                s_time = int(str(df.ix[:,col_name][df.station==source]).split(",")[0].split(" ")[4])
                d_time = int(str(df.ix[:,col_name][df.station==dest]).split(",")[0].split(" ")[4])
                
                if(s_time<d_time):
                    trains.append(train)
                    
                s_dist = int(str(df.ix[:,col_name][df.station==source]).split(",")[1].split("\n")[0])
                d_dist = int(str(df.ix[:,col_name][df.station==dest]).split(",")[1].split("\n")[0])
                
                dist = d_dist-s_dist
                
                distance[train]=dist

        find_trains(src,dst)

        for i in trains:
            cur = g.db.execute('select * from Train t where train_id = '+ str(i))           
            data.append([dict(Train_id=row[0], Train_Name=row[1], Source=row[2], Destination=row[3]) for row in cur.fetchall()])
        
        return render_template("user1.html", data=data)
    
    return render_template("user1.html")

#seats page contents
@app.route("/seats", methods=['GET', 'POST'])
@login_required
def seats():
    seats=[0,0,0,0]
    rate=[0,0,0,0]
    global trip_date
    global train_id
    train_id = request.form['train_id']
    global tot_dist
    tot_dist=distance[int(train_id)]

    def find_seats(train_id,trip_date):
        
        classes=['ac1','ac2','ac3','slr']
        g.db = connect_db()
    
        for t_class in classes:

            location = classes.index(t_class)

            df=pd.read_sql_query("select "+t_class+" from Class_Available where train_id=" + train_id + ";",g.db)
            default=int(str(df.ix[:,t_class]).split(" ")[4].split("\n")[0])
                
            df2=pd.read_sql_query("select train_id,trip_date,class,count(*) from Ticket where train_id=" + train_id + " and trip_date='" + trip_date + "' and class='" + t_class +"' group by class,trip_date,train_id order by trip_date;",g.db)
            if(str(df2.ix[:,'count(*)'])[0]=="S"):
                reserved=0;
            else:
                reserved=int(str(df2.ix[:,'count(*)']).split(" ")[4].split("\n")[0])
                
            seats[location] = default - reserved
                
            df3=pd.read_sql_query("select " + t_class + " from Class_Cost where train_id=" + train_id + ";",g.db)
            rate[location]=int(str(df3.ix[:,t_class]).split(" ")[4].split("\n")[0])
            
    find_seats(train_id,trip_date)

    data1 = { "train" : train_id, "ac1" : seats[0], "ac2" : seats[1], "ac3" : seats[2], "sleeper" : seats[3] }
    data2 = { "train" : train_id, "ac1" : rate[0], "ac2" : rate[1], "ac3" : rate[2], "sleeper" : rate[3] }
    return render_template("seats.html", data=data1, data2=data2)
            
#details page contents
@app.route("/details", methods=['GET', 'POST'])
@login_required
def details():
    global class_id
    class_id = request.form['class_id']
    
    return render_template("details.html", data=class_id)

#final page contents
@app.route("/final", methods=['GET', 'POST'])
@login_required
def final():
    global class_id
    global src
    global dst
    global train_id
    global trip_date
    global distance    
    global tot_dist  
    global names
    global ages
    global seat_nos  
    global seat_no
    seat_nos = []
    name1 = request.form['name1']
    age1 = request.form['age1']
    phone1 = request.form['phone1']
    name2 = request.form['name2']
    age2 = request.form['age2']
    phone2 = request.form['phone2']
    name3 = request.form['name3']
    age3 = request.form['age3']
    phone3 = request.form['phone3']
    name4 = request.form['name4']
    age4 = request.form['age4']
    phone4 = request.form['phone4']

    def find_time():
        g.db = connect_db()
        global src
        global dst
        global train_id
        global departure
        global arrival
        col_name = "s_" + str(train_id)
        df1 = pd.read_sql_query("SELECT "+col_name+" from Route where station='" + src+"';",g.db)
        df2 = pd.read_sql_query("SELECT "+col_name+" from Route where station='" + dst+"';",g.db)
        departure=str(df1.ix[:,col_name]).split(",")[0].split(" ")[4]
        arrival=str(df2.ix[:,col_name]).split(",")[0].split(" ")[4]

    find_time()

    dep_time = departure[0:2]+":"+departure[2:4]
    arr_time = arrival[0:2]+":"+arrival[2:4]
    
    def find_fare():
        global fare
        global train_id 
        global class_id 
        g.db = connect_db()
           
        df1 = pd.read_sql_query("SELECT "+class_id+" from Class_Cost where train_id=" + str(train_id) +";",g.db)
        
        fare = int(str(df1).split("\n")[1].split(" ")[2])
    
    find_fare()

    names = [name1, name2, name3, name4]
    ages = [age1, age2, age3, age4]
    j = 0
    for i in names:
        if i != '':
            j = j+1

    def new_ticket(t_name, t_age):
        g.db = connect_db()
        g.db.execute("insert into Ticket(name,age,train_id,trip_date,seat_no,fare,class,distance,destination,source,departure,arrival) values (?,?,?,?,?,?,?,?,?,?,?,?)", (t_name,t_age,train_id,trip_date,seat_no,fare,class_id,tot_dist,dst,src,int(departure),int(arrival)))
        g.db.commit()

    def allot_seats():
        global seat_no
        global seat_nos
        g.db = connect_db()
        df=pd.read_sql_query("select train_id,trip_date,class,count(*) from Ticket where train_id=" + train_id + " and trip_date='" + trip_date + "' and class='" + class_id +"' group by class,trip_date,train_id order by trip_date;",g.db)
        if(df.empty):
            seat_no = 0
        else:
            reserved=int(str(df.ix[:,'count(*)']).split(" ")[4].split("\n")[0])
            seat_no = reserved+1
            seat_nos.append(seat_no)
           
    for i in range(0,j):
        allot_seats()
        new_ticket(names[i], ages[i])
        

    return render_template("final.html",limit=j, dep=dep_time,fare=fare, arr=arr_time, name=names, age=ages, train=train_id, classs=class_id, trip=trip_date, source=src, dest=dst, dist=tot_dist, seat=seat_nos)


# route for handling the payment session
@app.route('/payment')
@login_required
def payment():
    return render_template("payment.html")    

# route for handling the logout session
@app.route('/logout')
@login_required
def logout():
        session.pop('logged_in', None)
        flash('You Are Logged Out')        
        return redirect(url_for('default'))

def connect_db():
    return sqlite3.connect(app.database)

if __name__ == "__main__":
    app.run(debug=True)