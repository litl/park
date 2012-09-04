Park is a persistent key-value API for Python with ordered traversal
of keys. Both keys and values are binary safe. It's similar in use to
LevelDB, but has no dependencies outside the Python standard library.

It is meant to be extremely easy to use and can scale to a few
gigabytes of data. It allows you to be lazy until it doesn't meet your
needs. Use it until then.

It supports simple getting and setting of byte data:

::

    >>> kv = park.SqliteStore("numbers.park")
    >>> kv.put("1", "one")
    >>> kv.put("2", "two")
    >>> kv.put("3", "three")
    >>> kv.put("4", "four")

    >>> kv.get("2")
    'two'

Batched setting of data from an iterable:

::

    >>> kv.put_many([("1", "one"), ("2", "two"), ("3", "three")])

    >>> kv.get("3")
    'three'

Lexically ordered traversal of keys and items, with start and end
sentinels (inclusive):

::

    >>> kv.put("1", "one")
    >>> kv.put("2", "two")
    >>> kv.put("3", "three")
    >>> kv.put("11", "eleven")
    >>> kv.put("12", "twelve")

    >>> list(kv.keys())
    ['1', '11', '12', '2', '3']

    >>> list(kv.keys(key_from="12"))
    ['12', '2', '3']

    >>> list(kv.keys(key_from="12", key_to="2"))
    ['12', '2']

    >>> list(kv.items(key_from="12"))
    [('12', 'twelve'), ('2', 'two'), ('3', 'three')]

Iteration over all keys or items with a given prefix:

::

    >>> kv.put("pet/dog", "Canis lupus familiaris")
    >>> kv.put("pet/cat", "Felis catus")
    >>> kv.put("pet/wolf", "Canis lupus")

    >>> list(kv.prefix_keys("pet/"))
    ['pet/cat', 'pet/dog', 'pet/wolf']

    >>> list(kv.prefix_keys("pet/", strip_prefix=True))
    ['cat', 'dog', 'wolf']

    >>> list(kv.prefix_items("pet/", strip_prefix=True))
    [('cat', 'Felis catus'),
     ('dog', 'Canis lupus familiaris'),
     ('wolf', 'Canis lupus')]

It plays well with generators, so you can e.g. park all the counting
numbers (this will take a while):

::

    def numbers():
        for num in itertools.count(1):
            key = value = str(num)
            yield key, value

    kv.put_many(numbers())

Or recursively park a directory's contents (keyed by relative paths)
from the local filesystem:

::

    def file_item(filename):
        with open(filename, "r") as fd:
            return filename, fd.read()

    kv.put_many(file_item(os.path.join(root, name))
                for root, dirs, files in os.walk(directory)
                for name in files)
