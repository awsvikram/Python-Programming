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
def note():
    if age < 18:
       print("You are too young to vote, Bud") 
    elif age < 21:
       print("Pal!You are old enough to vote,but too young to drink")
    elif 21 <= age < 65:
       print("Great job!You are old enough to vote and drink")
    else:
       print("You qualify for Social Security")
name()
calculateyear()
note()

