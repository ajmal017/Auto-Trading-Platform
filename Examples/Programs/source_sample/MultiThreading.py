import threading
import datetime


# global count
count = 0

def compIncrement(nums):
    global count
    for i in range(nums):
        count += i

def print_count():
    global count
    print(count)

# def main():
compIncrement(10000000)
print(count)

thread1 = threading.Thread(target=compIncrement, args=(10000000,))
thread2 = threading.Thread(target=print_count)


thread1.start()
# print(thread1.)
# thread1.join()
thread2.start()

# thread1.join()
# thread2.join()

print('Done!')


# if __name__ == '__main__':
#     main()

