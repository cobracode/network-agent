# coding: utf-8

import csv
import datetime
import logging
import os
import socket
import sys
import time
import urllib.request

# Global Constants
APP_NAME = 'Agent'
AUTHOR = 'Ned'
LOG_FILE = APP_NAME + '.log'
SCRIPT_NAME = os.path.basename(__file__)
VERSION = '2014.11.29.0'

MARGIN = '    '
SEPARATOR = '*' * 80

# Exception for stopping a script midway;
# STOP command
class StopScript(Exception):
    pass


class HTTP:
    def get(resource):
        return urllib.request.urlopen(resource)




class Networker:
    def __init__(self):
        self._socket = None
        self._localIP = None
        self._localPort = None
        self._remoteIP = None
        self._remotePort = None
        self._isConnected = False
        self._eol = '\n'


    def accept(self, ip, port, timeout):
        logging.debug("Networker.accept(): %s:%s %s sec timeout" % (ip, port, timeout))

        port = int(port)
        timeout = float(timeout)

        # Disconnect existing connection
        self.disconnect()

        # Avoid messing with our socket until a successful
        # connection is acheived. Use a temporary socket first
        # defaults: INET, TCP
        s = socket.socket()

        try:
            s.settimeout(timeout)
            s.bind((ip, port))

            # Listen for 1st connection
            logging.debug("Networker.accept(): Listening for %s seconds" % timeout)
            s.listen(1)

            # Upon connection, save socket
            (self._socket, address) = s.accept()
            (self._localIP, self._localPort) = self._socket.getsockname()
            self._remoteIP, self._remotePort = address[0], address[1]

            self._isConnected = True
            logging.debug("Networker.accept(): Accepted connection from %s:%s on %s:%s" %
                          (self._remoteIP, self._remotePort, self._localIP, self._localPort))
        except socket.timeout:
            logging.debug("Networker.accept(): Timed out listening for a connection.")
        except Exception as e:
            logging.debug("Networker.accept(): %s" % e)
            
        return self._isConnected


    def connect(self, ip, port, timeout):
        logging.debug("Networker.connect(): %s:%s %s sec timeout" % (ip, port, timeout))

        port = int(port)
        timeout = float(timeout)

        # Disconnect existing connection
        self.disconnect()

        # Try temporary socket first before saving it
        try:
            self._socket = socket.create_connection((ip, port), timeout)
            
            if self._socket:
                (self._remoteIP, self._remotePort) = self._socket.getpeername()
                (self._localIP, self._localPort) = self._socket.getsockname()
                
                logging.debug("Networker.connect(): connected to %s:%s from %s:%s" %
                              (self._remoteIP, self._remotePort, self._localIP, self._localPort))
                
                self._isConnected = True
        except Exception as e:
            logging.debug("Networker.connect(): %s" % e)

        return self._isConnected


    def disconnect(self):
        logging.debug("Networker.disconnect(): disconnecting")
        
        if self._isConnected:
            try:
                self._socket.shutdown(socket.SHUT_RDWR)
                self._socket.close()
                logging.debug("Networker.disconnect(): disconnected from %s:%s" % (self._remoteIP, self._remotePort))
            except Exception as e:
                logging.debug("Networker.disconnect(): %s" % e)

            self._isConnected = False
            self._localIP = None
            self._localPort = None
            self._remoteIP = None
            self._remotePort = None
            self._socket = None


    def httpGet(self, resource):
        result = False

        print(HTTP.get(resource).getheaders())

        return result


    def listen(self, listenTime):
        result = True
        data = b''

        if self._isConnected:
            listenTime = float(listenTime)

            self._socket.settimeout(0.5)
            
            # Listen for specified number of seconds
            # reading a bit at a time and sleeping for short time.
            # Contentate results and tokenize by EOL
            endtime = datetime.datetime.utcnow() + datetime.timedelta(seconds=listenTime)
            logging.debug("Networker.listen(): endtime = %s" % endtime)
            
            while endtime >= datetime.datetime.utcnow():
                secondsLeft = float((endtime - datetime.datetime.utcnow()).seconds)
                logging.debug("Networker.listen(): seconds left: %s" % secondsLeft)

                try:
                    # For best performance, keep power of 2 relatively small
                    newData = self._socket.recv(2**11)                    
                    logging.debug("Networker.listen(): received: %s" % repr(newData))
                    data += newData
                except socket.timeout:
                    # Break out of the loop as we have read all the data
                    break
                except socket.error as e:
                    logging.debug("Networker.listen(): %s" % e)
                    result = False
                    break

                time.sleep(0.1)

            # Now that we've got all our data, UTF-8 encode and tokenize it
            data = str(data, encoding='utf-8').split(self._eol)
            [logging.debug("%s %s" % (MARGIN, line)) for line in data if line]
        else:
            logging.debug("Networker.listen(): Cannot listen without a connection")
            result = False

        return (result, data)


    def send(self, data):
        result = False

        if self._isConnected:
            try:
                message = data + self._eol
                self._socket.sendall(bytearray(message, encoding='utf-8'))
                logging.debug("Networker.send(): sent: %s" % repr(message))
                result = True
            except Exception as e:
                logging.debug("Networker.send(): %s" % e)
        else:
            logging.debug("Networker.send(): Cannot send without a connection.")

        return result


    def setEOL(self, eol):
        self._eol = eol


#------------------------------------------------------------------

class ScriptRunner:    
    # Constructor
    def __init__(self, script):
        self._scriptFile = script
        self._networker = Networker()

    
    def run(self):
        numErrors = 0

        # Open CSV file for reading
        try:
            reader = csv.reader(open(self._scriptFile, mode='r', encoding='utf-8'))
        except OSError as e:
            logging.error("Error reading script file: %s" % e)
            numErrors += 1
            return numErrors

        lineNumber = 1

        # Read each line
        for line in reader:
            # Uncomment if needed
            #logging.debug("ScriptRunner.run(): line %s = %s" % (lineNumber, repr(line)))

            # Skip comments and blank lines
            if len(line) != 0 and '#' != line[0][0]:
                logging.debug("ScriptRunner.run(): line %s = %s" % (lineNumber, repr(line)))

                # Remove escape sequences
                line = [word.encode('utf-8').decode('unicode_escape') for word in line if word]
                
                # Get command, which is always uppercase
                command = line[0].upper().strip()

                # Execute command if valid
                if command in COMMANDS:
                    methodCall = getattr(self, command)

                    try:
                        if not methodCall(lineNumber, line[1:]):
                            logging.error("Line %s: %s failed." % (lineNumber, command))
                            numErrors += 1
                    except StopScript:
                        break
                    except Exception as e:
                        logging.error(e)
                        break
                else:
                    logging.error("ScriptRunner.run(): Line %s: Unknown command \"%s\"." % (lineNumber, command))
                    numErrors += 1
            
            lineNumber += 1

        self.DISCONNECT()

        return numErrors

    
    # --------- Script Commands -----------
    # keep in alphabetical order
    # -------------------------------------

    # Accept connections from IP, port
    # accept,localhost,5555,10
    def ACCEPT(self, line, args):
        result = False

        if len(args) > 2:
            ip, port, timeout = args[0], int(args[1]), float(args[2])
            logging.info("Line %s: LISTENING for connection on %s:%s with %s sec timeout" % (line, ip, port, timeout))
            
            result = self._networker.accept(ip, port, timeout)
        else:
            logging.error("Line %s: ACCEPT: IP and/or port and/or timeout not specified. Args: %s" % (line, args))
        
        return result


    # Connect to IP:port with timeout
    # connect,www.google.com,80,5
    def CONNECT(self, line, args):
        result = False

        if len(args) > 2:
            ip, port, timeout = args[0], int(args[1]), float(args[2])
            logging.info("Line %s: CONNECT: attempting to connect to %s:%s with %s sec timeout" % (line, ip, port, timeout))
            result = self._networker.connect(ip, port, timeout)
        else:
            logging.error("Line %s: CONNECT: unspecified IP and/or port and/or timeout" % line)

        return result


    # Disconnect
    # disconnect
    def DISCONNECT(self, line=None, args=None):
        if line:
            logging.info("Line %s: Disconnecting" % line)
        else:
            logging.info("Disconnecting")
            
        self._networker.disconnect()
        return True


    # Echo
    # echo,this is a test
    def ECHO(self, line, args):
        message = args[0] if args else ''
        logging.info("Line %s: ECHO: %s" % (line, message))
        return True


    # Set the EOL for talking across network
    # eol,\r\n
    def EOL(self, line, args):
        eol = args[0] if args else '\n'
        self._networker.setEOL(eol)
        logging.info("Line %s: Setting EOL to: %s" % (line, repr(eol)))
        return True


    # Send HTTP 1.1 GET request over connection
    # httpget,/site.html
    def HTTPGET(self, line, args):
        result = False

        if args:
            resource = args[0]
            logging.info("Line %s: HTTP GET for %s" % (line, resource))

            (result, data) = self._networker.httpGet(resource)
        else:
            logging.error("Line %s: HTTP GET missing resource name." % line)
            
        return result


    # Listen for data on existing connection
    # listen,5
    def LISTEN(self, line, args):
        result = False

        if args:
            time = float(args[0])

            logging.info("Line %s: LISTENING for %s sec for data from connection." % (line, time))
            (result, data) = self._networker.listen(time)
        else:
            logging.error("Line %s: LISTEN command missing time (sec) parameter." % line)
        
        return result


    # Send on connection
    # send,sending this message
    def SEND(self, line, args):
        result = False
        
        if args:
            data = args[0]
            logging.info("Line %s: SENDING data: %s" % (line, repr(data)))
            result = self._networker.send(data)
        else:
            logging.error("Line %s: SEND command missing data parameter." % line)

        return result


    # Stop running the script
    # stop
    def STOP(self, line, args):
        logging.info("Line %s: STOPPING script run." % line)
        raise StopScript

# ---------------------------------------------------------------

COMMANDS = [command for command in dir(ScriptRunner) if command.isupper()]


def initLog():
    format = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s")

    fileHandler = logging.FileHandler(LOG_FILE)
    screenHandler = logging.StreamHandler()

    fileHandler.setFormatter(format)
    screenHandler.setFormatter(format)

    fileHandler.setLevel(logging.DEBUG)
    screenHandler.setLevel(logging.DEBUG)

    logging.getLogger('').addHandler(fileHandler)
    logging.getLogger('').addHandler(screenHandler)
    logging.getLogger('').setLevel(logging.DEBUG)


def showUsage():
    logging.info(SEPARATOR)
    logging.info(MARGIN + APP_NAME)
    logging.info(MARGIN + VERSION)
    logging.info('')
    logging.info(MARGIN + 'Description: Simple TCP Client/Server. Send/receive data to/from any IP and port.')
    logging.info('')
    logging.info(MARGIN + 'Usage: ' + SCRIPT_NAME + ' some_server.csv [some_client.csv ...]')
    logging.info('')
    logging.info(MARGIN + 'Available script commands:')
    logging.info('')

    [logging.info(MARGIN + command) for command in COMMANDS]

    logging.info('')
    logging.info(MARGIN + 'Last edited by: ' + AUTHOR)
    logging.info(SEPARATOR)

# --------------------------------- MAIN ---------------------------------------

if '__main__' == __name__:
    initLog()

    # Process arguments
    args = sys.argv
    logging.debug("main(): args = %s" % repr(args))

    if 1 < len(args):
        # Get script files
        scripts = args[1:]
        numScripts = len(scripts)
        logging.debug("main(): scripts = %s" % repr(scripts))

        # Display files for clarity
        logging.info(APP_NAME)
        logging.info("v%s" % VERSION)
        logging.info('')
        logging.info("Will run %s script(s)." % numScripts)
        logging.info('')
        [logging.info("%s%s" % (MARGIN, script)) for script in scripts]
        logging.info('')

        errorlessScripts = 0
        numFailures = 0

        # Run the scripts
        for script in scripts:
            logging.info("Running script \"%s\"" % script)
            logging.info('')
            
            runner = ScriptRunner(script)
            latestFailures = runner.run()

            if 0 < latestFailures:
                numFailures += latestFailures
            else:
                errorlessScripts += 1

            logging.info('')

        logging.info('')
        logging.info("Ran %s/%s scripts without failure." % (errorlessScripts, numScripts))
        logging.info("[%s] Failed Command" % numFailures)
    else:
        showUsage()
