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
$ pip install -r requirements.txt  # different from tsung requirements
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
$ py.test -k test_models  # run model tests
$ py.test -k test_basic  # run test_models.test_basic
$ py.test -m <sql or couch> # only run the sql or couch tests
$ py.test --rowsize <form or case> # run the rowsize form or case tests

```


## Tsung Tests

## Get tsung

```
$ sudo git clone https://github.com/processone/tsung.git /usr/local/src/tsung --depth=1
$ cd /usr/local/src/tsung
$ ./configure
$ sudo make install
```

### Tsung dependencies
- autoconf
- automake
- erlang-base
- erlang-crypto
- erlang-eunit
- erlang-inets
- erlang-snmp
- erlang-ssl
- erlang-xmerl
- erlang-dev
- erlang-asn1
- gnuplot

Also Perl Template module for generating the reports:
```
$ sudo cpan Template
```


## Running tests against production environment

### Initial setup

```
$ sudo -iu cchq bash
$ source ~/.virtualenvs/tsung/bin/activate
$ pip install -r requirements.txt  # Only necessary if there are new deps
$ ulimit -n 65536  # Make sure enough file descriptors are available
```

* Create domain for testing on the environment you want to test against.
* Turn of secure submissions in project settings.
* Copy `localsettings.example.py` to `localsettings.py` 
and update as necessary with the enpoint you want to test and the 
test plans you want to run.
* Create `userdb` and `casedb` for the env you're testing (See below)
* Run test command:

```
$ invoke awesome_test --endpoint=my_endpoint --testrun=fancytest
```


### Createing the `userdb`

The user DB is a database of users that Tsung randomizes when 
To load the database you can use:
```
$ invoke load_db <scale_factor> <backend>
```



* make prod backend with ssl type and port 443
* instructions on creating userdb & casedb (only needed for case updates)
* update form templates to use current date and time 
