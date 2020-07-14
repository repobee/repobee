### Deadline
This work should be completed before the exercise on **Friday 13th September**.

### Instructions
For instructions on how to do and submit the assignment, please see the
[assignments section of the course instructions](https://gits-15.sys.kth.se/inda-19/course-instructions#assignments).

### Homework
Study sections 2.1 -- 2.12 and 2.15 -- 2.18 in _Objects First with Java_ (5th
or 6th ed) (don't mind the mentions of _if/else_, that is covered next week).

Please complete exercises 2.1 -- 2.42. You do not need to submit this homework,
but you must be prepared to discuss it.

You do not need to do the exercises in 2.15 -- 2.18, other than the ones in
the Github task!

You can find the code for TicketMachine in the
[bluej-projects repo](https://gits-15.sys.kth.se/inda-19/bluej-projects/tree/master/chapter02/naive-ticket-machine).

### Github Task:
Submit code for tasks:

* 2.44 -- 2.45
* 2.58 -- 2.61

> **Assistant's note:** Remember that the name of the class and the name of the
> file must match exactly, including capitalization. That is to say, if the
> public class in the file is called `TicketMachine`, then the file must be
> called `TicketMachine.java`, or the code will not compile.

Please commit any written answers to the [`docs`](docs) folder, and commit any Java code
developed to the [`src`](src) folder of your KTH Github repo. Remember to push to KTH
Github.

#### Exercise 2.44
Give the class two constructors. One should take a single parameter that
specifies the `price`, and the other should take no parameter and set the
`price` to be a default value of your choosing.  Test your implementation by
creating machines via the two different constructors.

> **Assistant's note:** Please note that there are two versions of `TicketMachine` in Chapter 2. You may use choose either one with no problem for the exercises.

#### Exercise 2.45
Implement a method `empty`, that simulates the effect of removing all money from
the machine.  This method should have a `void` return type, and its body should
simply set the `total` field to zero. Does this method need to take any
parameters? Test your method by creating a machine, inserting some money,
printing some tickets, checking the total, and then emptying the machine.  Is
the `empty` method a mutator or an accessor?

#### Exercise 2.58
Why does the following version of refundBalance not give the same results as
the original?

```java
public int refundBalance()
{
    balance = 0;
    return balance;
}
```
What tests can you run to demonstrate that it does not?

#### Exercise 2.59
What happens if you try to compile the TicketMachine class with the following
version of refundBalance?

```java
public int refundBalance()
{
    return balance;
    balance = 0;
}
```
What do you know about return statements that helps to explain why this version
does not compile?

#### Exercise 2.60
What is wrong with the following version of the constructor of TicketMachine?

```java
public TicketMachine(int cost)
{
    int price = cost;
    balance = 0;
    total = 0;
}
```
Try out this version in the better-ticket-machine project. Does this version
compile? Create an object and then inspect its fields. Do you notice something
wrong about the value of the price field in the inspector with this version?
Can you explain why this is?

#### Exercise 2.61
Add a new method, emptyMachine, that is designed to simulate emptying the
machine of money. It should reset total to be zero but also return the value
that was stored in total before it was reset.

### Grading Criteria
Each week we will communicate grading criteria through the [issue tracker](../../issues/). Grading criteria set the basic standards for a pass, komp or fail, so it is essential you review them each week. These will change over time as your skills develop, so make sure you read the grading criteria issue carefully and tick off all the requirements.
