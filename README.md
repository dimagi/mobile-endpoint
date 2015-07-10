# mobile-endpoint

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
