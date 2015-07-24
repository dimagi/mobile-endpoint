# mobile-endpoint

Libraries for loadtesting CommCare HQ's new form and case processing/retore engine.

This repository mainly consists of two components:

- A prototype endpoint (with swappable backends) for processing forms and cases and restoring data to phones
- A suite of load testing tools (including tests of the prototype) built on tsung.

## Prototype

### Prerequisites

These tests depend on Postgres 9.4 since they make use of the jsonb column type. They also depend on Redis 2.6 or later .

See [http://www.postgresql.org/docs/9.4/static/upgrading.html] for information about upgrading your local postgres.

To upgrade redis you can just install a new version over your existing one.


### Installation

To setup an environment for the prototype make a new virtualenv and install requirements:

```
$ makevirtualenv --no-site-packages mobile-endpoint
$ cd prototype/
$ pip install requirements.txt  # different from tsung requirements
```

### Running tests

In the prototype directory first setup a `localconfig.py` and `testconfig.py` and edit the connection string (and anything else as necessary).
`localconfig.py` just needs to exist (and will be used for running the server).
`testconfig.py` overrides `localconfig.py` when running tests.

```
$ cp localconfig.example.py localconfig.py
$ cp testconfig.example.py testconfig.py
```

Once your settings are updated you can run tests as follows

```
$ py.test  # run all tests
$ py.test test_models  # run model tests
$ py.test test_basic  # run test_models.test_basic
```


## Tsung Tests

### Loading the database

To load the database you can use `invoke`. First initialize the DB:

```
invoke init_db
```

Next load the DB with some tests data:

```
invoke load_db <scale_factor>
```

### Configuring Tsung

First you'll need to generate the Tsung config. Make your localsettings for Tsung are correct.To build the
Tsung XML conf (can be found in `tsung/build`):
```
invoke tsung_build
```

Next you need to compile and link the erlang files so that Tsung knows about them:
```
invoke tsung_erl_build
```

If you want to just do this in one step:

```
invoke tsung_hammer
```

### Running Tsung on indiacloud6
```
$ sudo -iu cchq bash
$ source ~/.virtualenvs/tsung/bin/activate
$ pip install -r requirements.txt  # Only necessary if there are new deps
$ invoke tsung_hammer
$ ulimit -n 65536  # Make sure enough file descriptors are available
$ tsung -f ~/.tsung/mobile-endpoint/tsung/build/<config> start
```
