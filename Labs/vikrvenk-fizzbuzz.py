x = int(input("Enter the range:")) 
print(type(x))
for fizbuzz in range(x):
    if fizbuzz % 3 == 0 and fizbuzz % 5 == 0:
       print("Fizzbuzz")
       continue
    elif fizbuzz % 3 == 0:
       print("Fizz")
       continue
    elif fizbuzz % 5 == 0:
       print("Buzz")
       continue
