### Deadline
This work should be completed before the exercise on **Friday 20th September**.

### Instructions
For instructions on how to do and submit the assignment, please see the
[assignments section of the course instructions](https://gits-15.sys.kth.se/inda-19/course-instructions#assignments).

### Homework
Study sections 2.13, 2.14 and 2.19 -- 2.23 of the course textbook (5th or 6th
ed).

Please complete exercises 2.52 -- 2.57 and 2.62 -- 2.63 (from last week's
reading material) and also 2.64 -- 2.82. You do not need to submit this
homework, but you must be prepared to discuss it.

### Github Task:
Choose **one** of the following tasks:

- Submit code for tasks 2.83 -- 2.90 in the form of **a complete Java source
  code file** called `Book.java`.

or

- Submit code for tasks 2.92 -- 2.93 the form of **a complete Java source code
  file** called `Heater.java`.

> **Assistant's note:** Again, do not forget to double check that the names
> of your class and `.java` file match!

Please commit any written answers to the [`docs`](docs) folder, and commit any Java code
developed to the [`src`](src) folder of your KTH Github repo. Remember to push to KTH
Github.

### _Option 1: Book

#### Exercise 2.83
Below is the outline for a Book class, which can be found in the book-exercise
project. The outline already defines two fields and a constructor to initialize
the fields. In this and the next few exercises, you will add features to the
class outline.

Add two accessor methods to the class - `getAuthor` and `getTitle` - that return
the `author` and `title` fields as their respective results. Test your class by
creating some instances and calling the methods.

```java
  /**
   * A class that maintains information on a book.
   * This might form part of a larger application such
   * as a library system, for instance.
   *
   * @author (Insert your name here.)
   * @version (Insert today’s date here.)
   */
  public class Book
  {
      // The fields.
      private String author;
      private String title;
      /**
       * Set the author and title fields when this object
       * is constructed.
       */
      public Book(String bookAuthor, String bookTitle)
      {
          author = bookAuthor;
          title = bookTitle;
      }
      // Add the methods here...
  }
```

#### Exercise 2.84
Add two methods, `printAuthor` and `printTitle`, to the outline Book class.
These should print the `author` and `title` fields, respectively, to the
terminal window.

#### Exercise 2.85
Add a field, `pages`, to the Book class to store the number of pages. This
should be of type `int`, and its initial value should be passed to the single
constructor, along with the author and title strings. Include an appropriate
`getPages` accessor method for this field.

#### Exercise 2.86
Add a method, `printDetails`, to the Book class. This should print details of
the author, title, and pages to the terminal window. It is your choice how the
details are formatted. For instance, all three items could be printed on a
single line, or each could be printed on a separate line.  You might also choose
to include some explanatory text to help a user work out which is the author and
which is the title, for example:

_Title: Robinson Crusoe, Author: Daniel Defoe, Pages: 232_

#### Exercise 2.87
Add a further field, `refNumber`, to the Book class. This field can store a
reference number for a library, for example. It should be of type `String` and
initialized to the zero length string ("") in the constructor, as its initial
value is not passed in a parameter to the constructor. Instead, define a mutator
for it with the following header:

```java
public void setRefNumber(String ref)
```

The body of this method should assign the value of the parameter to the
`refNumber` field. Add a corresponding `getRefNumber` accessor to help you check
that the mutator works correctly.

#### Exercise 2.88
Modify your `printDetails` method to include printing the reference number.
However, the method should print the reference number only if it has been set —
that is, the `refNumber` string has a non-zero length. If it has not been set,
then print the string "ZZZ" instead. Hint: Use a conditional statement whose
test calls the length method on the `refNumber` string.

#### Exercise 2.89
Modify your `setRefNumber` mutator so that it sets the `refNumber` field only if
the parameter is a string of at least three characters. If it is less than
three, then print an error message and leave the field unchanged.

#### Exercise 2.90
Add a further integer field, `borrowed`, to the Book class. This keeps a count
of the number of times a book has been borrowed. Add a mutator, `borrow`, to the
class. This should update the field by 1 each time it is called. Include an
accessor, `getBorrowed`, that returns the value of this new field as its result.
Modify `printDetails` so that it includes the value of this field with an
explanatory piece of text.

### _Option 2: Heater

#### Exercise 2.92
Create a new project, heater-exercise, within BlueJ. Edit the details in the
project description — the text note you see in the diagram. Create a class,
`Heater`, that contains a single field, `temperature` whose type is
double-precision floating point — see Appendix B, section B.1, for the Java type
name that corresponds to this description.

Define a constructor that takes no parameters. The `temperature` field should be
set to the value 15.0 in the constructor. Define the mutators `warmer` and
`cooler`, whose effect is to increase or decrease the value of temperature by
5.0° respectively. Define an accessor method to return the value of temperature.

#### Exercise 2.93
Modify your `Heater` class to define three new double-precision floating point
fields: `min`, `max`, and `increment`. The values of `min` and `max` should be
set by parameters passed to the constructor. The value of increment should be
set to 5.0 in the constructor. Modify the definitions of `warmer` and `cooler`
so that they use the value of `increment` rather than an explicit value of 5.0.
Before proceeding further with this exercise, check that everything works as
before.

Now modify the `warmer` method so that it will not allow the temperature to be
set to a value greater than `max`. Similarly modify `cooler` so that it will not
allow temperature to be set to a value less than `min`. Check that the class
works properly. Now add a method, `setIncrement`, that takes a single parameter
of the appropriate type and uses it to set the value of `increment`. Once again,
test that the class works as you would expect it to by creating some Heater
objects within BlueJ. Do things still work as expected if a negative value is
passed to the `setIncrement` method?  Add a check to this method to prevent a
negative value from being assigned to `increment`.

### Grading Criteria
Each week we will communicate grading criteria through the [issue tracker](../../issues/). Grading criteria set the basic standards for a pass, komp or fail, so it is essential you review them each week. These will change over time as your skills develop, so make sure you read the grading criteria issue carefully and tick off all the requirements.
