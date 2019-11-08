from datetime import datetime 
def name():
    print("Hello " + lname + "," + fname)
fname = input("Enter the First Name:")
lname = input("Enter the last name: ")
age = int(input("What is your age?"))
def calculateyear():
    today = int(datetime.now().strftime('%Y'))
#    yearborn = today - age
    print("Your birth year is " + str(today - age)) 
name()
calculateyear()

