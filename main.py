from datetime import datetime
from itertools import product
from flask import Flask,render_template,request,redirect,flash,url_for
from flask_login.utils import login_required, set_login_view
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField,PasswordField
from wtforms.fields.html5 import EmailField
from wtforms.validators import InputRequired,Length,ValidationError,EqualTo
from flask_login import LoginManager,login_user,current_user,logout_user,UserMixin
from passlib.hash import pbkdf2_sha256
import enum
import os

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://fwujkgaxqebzbf:5ae0562bdaf8164544d99dd3c17e01c8d491bb6f15b1252e9c91d073ecf3361e@ec2-54-83-82-187.compute-1.amazonaws.com:5432/dccpathndkeckv"
app.config['SECRET_KEY'] ="Some random string for protection"
db = SQLAlchemy(app)
login = LoginManager(app)
login.init_app(app)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR_APP = os.path.dirname(os.path.abspath(__file__))

class EmploymentStatusEnum(enum.Enum):
    approved = 'Approved'
    unapproved = 'Unapproved'


class User(UserMixin,db.Model):
	__tablename__ = "users"
	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(12), unique=True, nullable=False)
	email = db.Column(db.String(40), nullable=False, unique = False)
	password = db.Column(db.String(200),nullable=False)

class Product(db.Model):
	__tablename__ = "Products"
	id = db.Column(db.Integer,primary_key=True)
	Name = db.Column(db.String(25),nullable=False)
	Price = db.Column(db.Integer,nullable=False)
	desc= db.Column(db.String(100),nullable=False)
	Posted_By= db.Column(db.String(20),nullable=False)
	Date = db.Column(db.DateTime,default=datetime.now)
	category = db.Column(db.String(20),nullable=False)
	location=db.Column(db.String(100),nullable=True)
	fileName = db.Column(db.String(100),nullable=True)
	Approved = db.Column(db.Enum(EmploymentStatusEnum),default=EmploymentStatusEnum.unapproved,nullable=False)

class Message(db.Model):
	__tablename__ = "Messages"
	id = db.Column(db.Integer,primary_key=True)
	SendTo = db.Column(db.String(18))
	SendBy = db.Column(db.String(18))
	message = db.Column(db.String(100),nullable=False)
	Date = db.Column(db.DateTime,default=datetime.now)

class Registration(FlaskForm):
	username = StringField('username', validators=[InputRequired(message="Username required"), Length(min=4, max=12, message="Username must be between 4 and 25 characters")])
	email = EmailField("email", validators=[InputRequired("Please Enter valid email address"),Length(min=8, max=40, message="Email must be between 8 to 20 characters")])
	password = PasswordField("password", validators=[InputRequired("password required"),Length(min=6, max=18, message="Password must be between 6 to 18 characters")])
	confirm = PasswordField("confirm",validators=[InputRequired("Password required"),EqualTo("password",message="Password must match")])

	def validate_username(self,username):
		user_object = User.query.filter_by(username=username.data).first()
		if user_object:
			raise ValidationError("Username already Exists!")


def validator(form,field):
	username = form.username.data
	password = field.data
	user_data = User.query.filter_by(username=username).first()
	if user_data is None:
		raise ValidationError("Username or Password Incorrect")
	elif(not pbkdf2_sha256.verify(password,user_data.password)):
		raise ValidationError("Username or Password Incorrect")
	else:
		return True

class Login(FlaskForm):
	username = StringField('username', validators=[InputRequired(message="Username required"), Length(min=4, max=25, message="Username must be between 4 and 25 characters")])
	password = PasswordField("password", validators=[InputRequired("password required"),validator])



@login.user_loader
def load_user(user_id):
	return User.query.filter_by(id=user_id).first()


@app.route("/login",methods= ["GET","POST"])
def login():
	login_form = Login()
	if login_form.validate_on_submit():
		username = login_form.username.data
		user = User.query.filter_by(username=username).first()
		login_user(user)
		if(current_user.is_authenticated):
			return redirect("/")
		else:
			return redirect("register")
	return render_template("login.html",login=login_form)


@app.route("/register",methods=["GET","POST"])
def register():
	register = Registration()
	message = None
	if register.validate_on_submit():
		username = register.username.data
		email = register.email.data
		password = register.password.data
		enc = pbkdf2_sha256.hash(password)
		user =  User(username=username,email=email,password=enc)
		db.session.add(user)
		try:
			db.session.commit()
			message = "User Successfully Registered"
			return redirect("/login")
		except:
			message = "Something Error Happened"
	return render_template("register.html",reg_form=register,message=message)

@app.route("/",methods=["GET","POST"])
def homepage():
	#if(not current_user.is_authenticated):
	#	return redirect("/login")
	category = Product.query.filter_by(Approved="approved").all()
	sets = {i.category for i in category}
	allProd = []
	for i in sets:
		data = Product.query.filter_by(category=i).all()
		allProd.append(data)
	return render_template("ads.html",data= allProd,base_dir=BASE_DIR)


@app.route("/add",methods=["GET","POST"])
@login_required
def add():
	message = None
	if(request.method == "POST"):
		name = request.form.get("name")
		price = request.form.get("price")
		desc= request.form.get("desc")
		category = request.form.get("category")
		street = request.form.get("street-address")
		city = request.form.get("city")
		state = request.form.get("state")
		zip = request.form.get("postal-code")
		image= request.files['file-upload']
		#image.save(os.path.join(BASE_DIR,f"app/static/media/{image.filename}"))
		image.save(os.path.join(BASE_DIR_APP,f"static/media/{image.filename}"))
		product = Product(Name=name,Price=price,desc=desc,category=category,location=street+" "+city+" "+state+ " "+zip,fileName=image.filename,Posted_By=current_user.username)
		db.session.add(product)
		try:
			db.session.commit()
			message= "Project Successfully Published and send for approval"
			return redirect("/")
		except:
			message="Project Cant Published due to some error!"

	return render_template("add.html",message=message)

@app.route("/product/<string:id>",methods=["GET","POST"])
@login_required
def productView(id):
	message = None
	Products = Product.query.filter_by(id=id).first()
	publisherName = Products.Posted_By
	if request.method == "POST":
		message = request.form.get("message-text")
		data = Message(SendTo=publisherName,SendBy=current_user.username,message=message)
		db.session.add(data)
		try:
			db.session.commit()
			message= "Message Sended Successfully"
		except:
			message="Cant Send Message right now"
	return render_template("view.html",product=Products,message=message,base_dir=BASE_DIR)



@app.route("/message",methods=["GET","POST"])
@login_required
def message():
	messages = None
	MessageData = Message.query.filter_by(SendTo=current_user.username).all()
	SendedMessage = Message.query.filter_by(SendBy=current_user.username).all()
	print(SendedMessage)
	if request.method == "POST":
		name = request.form.get("recipient-name")
		message = request.form.get("message-text")
		data = Message(SendTo=name,SendBy=current_user.username,message=message)
		db.session.add(data)
		try:
			db.session.commit()
			messages = "Message Sended Successfully"
		except:
			messages = "Cant Send Message right now"
	return render_template("message.html",messages=MessageData,send=SendedMessage,message=messages)


@app.route("/admin",methods=["GET","POST"])
@login_required
def admin():
	if(not current_user.is_authenticated and current_user.username != "admin"):
		return redirect("/")
	adData = Product.query.all()
	userData = User.query.all()
	return render_template("admin.html",product=adData,user=userData)



@app.route("/admin/<string:id>",methods=["GET","POST"])
@login_required
def projectEdit(id):
	if(not current_user.is_authenticated and current_user.username != "admin"):
		return redirect("/")
	ProjectData = Product.query.filter_by(id=id).first()
	message = None
	if(request.method=="POST"):
		name = request.form.get("name")
		price = request.form.get("price")
		desc = request.form.get("desc")
		postedBY = request.form.get("postedBy")
		pstatus = request.form.get("status")
		category = request.form.get("category")
		filename = request.form.get("filename")
		location= request.form.get("location")
		ProjectData.Name=name
		ProjectData.Price = price
		ProjectData.desc = desc
		ProjectData.Posted_By = postedBY
		ProjectData.Approved = pstatus
		ProjectData.category = category
		ProjectData.fileName = filename
		ProjectData.location = location
		try:
			db.session.commit()
			message = "Project Successfully Updated"
			return redirect("/admin")
		except:
			message = "Project Cant be updated right now"
	return render_template("edit.html",project=ProjectData,base_dir=BASE_DIR,message=message)

@app.route("/admin/delete/<string:id>",methods=["GET","POST"])
@login_required
def projectDelete(id):
	if(not current_user.is_authenticated and current_user.username != "admin"):
		return redirect("/")
	ProjectData = Product.query.get_or_404(id)
	db.session.delete(ProjectData)
	db.session.commit()
	message = "Project is deleted successfully"
	return redirect("/admin")

@app.route("/admin/delete/user/<string:id>",methods=["GET","POST"])
@login_required
def userDelete(id):
	if(not current_user.is_authenticated and current_user.username != "admin"):
		return redirect("/")
	user = User.query.get_or_404(id)
	db.session.delete(user)
	db.session.commit()
	message = "User is deleted successfully"
	return redirect("/admin")

@app.route("/logout")
def logout():
	logout_user()
	return redirect("/login")

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html')

if __name__ == "__main__":
    app.run()
