# mobile-endpoint

## Get tsung

```
$ sudo git clone https://github.com/processone/tsung.git /usr/local/src/tsung
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


## Running tests on indiacloud8

Use the `awesome_test` task to run the tests. e.g.
```
$ sudo -iu cchq bash
$ source ~/.virtualenvs/tsung/bin/activate
$ pip install -r requirements.txt  # Only necessary if there are new deps
$ ulimit -n 65536  # Make sure enough file descriptors are available
$ invoke awesome_test --duration=60 --load=100 --backend=prototype --user-rate=250
```
The `load` flag is optional. If not included, no new forms or cases will be loaded into the database before running the test.


### Loading the database without a test

To load the database you can use:
```
$ invoke load_db <scale_factor> <backend>
```
