#!/usr/bin/env python
#-*- coding: utf-8 -*-

try:
    from splinter import Browser
except:
    print "Please install Splinter: http://splinter.readthedocs.org/en/latest/install.html"
    sys.exit()

import sys, getopt, re, os, threading
from datetime import datetime
from time import sleep
from splinter.request_handler.status_code import HttpResponseError

activeThreads = 0
program = True

def main(argv):
    print "Loading..."
    d = datetime.now()
    date = str(d.year) + '' + str(d.month) + '' + str(d.day) + '' + str(
        d.hour) + '' + str(d.minute) + '' + str(d.second)
    users = None
    txt = None
    proxy = False
    maxThreads = 0
    global program

    try:
        opts, args = getopt.getopt(argv, "hi:u:t:p:", ["file=", "users=", "threads=", "proxy", "help"])
    except getopt.GetoptError:
        print 'Use --help for help'
        sys.exit(2)

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print 'Usage: {0} <options> \n'.format(os.path.basename(__file__))
            print '     -h, --help              This help'
            print '     -u, --users FILE        File with twitter accounts'
            print '     -i, --file FILE         File with twitter URLs list'
            print '     -p, --proxy             Use privoxy + tor'
            print '     -t, --threads           Number of threads to use'
            sys.exit()
        elif opt in ("-i", "--file"):
            txt = arg
        elif opt in ("-u", "--users"):
            users = arg
        elif opt in ("-p", "--proxy"):
            proxy = True
        elif opt in ("-t", "-threads"):
            try:
                maxThreads = int(arg)
            except:
                print "Thread value not valid."
                sys.exit()

    if maxThreads == 0:
        maxThreads = 3

    if not users or not txt:
        print 'Use --help for help\n'
        print 'Usage: python {0} -u <accounts_list.txt> -i <twitter_list.txt>'.format(os.path.basename(__file__))
        print 'The accounts list must have only 1 account per line'
        sys.exit()

    global activeThreads

    usersFile = open(users, 'r')
    reporters = ()
    for line in usersFile:
        datas = line.split(' ')
        try:
            while activeThreads >= maxThreads:
                sleep(10)
            print "Logging with username: {0} and password: {1}".format(datas[0], datas[1])
            if proxy:
                proxyIP = '127.0.0.1'
                proxyPort = 8118
                proxy_settings = {'network.proxy.type': 1,
                        'network.proxy.http': proxyIP,
                        'network.proxy.http_port': proxyPort,
                        'network.proxy.ssl': proxyIP,
                        'network.proxy.ssl_port':proxyPort,
                        'network.proxy.socks': proxyIP,
                        'network.proxy.socks_port':proxyPort,
                        'network.proxy.ftp': proxyIP,
                        'network.proxy.ftp_port':proxyPort
                        }
                browser = Browser('firefox',profile_preferences=proxy_settings)
            else:
                browser = Browser()
            tempThread = threading.Thread(target = lineReporter, args = (
                datas, browser, txt, users, date))
            tempThread.daemon = True
            tempThread.start()
            activeThreads += 1
            reporters = reporters + (tempThread,)
        except KeyboardInterrupt:
            program = False
            while activeThreads is not 0:
                sleep(5)
            print "\nQuit by keyboard interrupt sequence!\n"
            sys.exit()
    while activeThreads != 0:
        sleep(20)
    sys.exit()

def lineReporter(datas, browser, txt, users, date):

    global activeThreads
    global program

    username = datas[0]
    password = "{0}".format(datas[1].rstrip('\n'))

    browser.visit("https://twitter.com/login")
    browser.execute_script("$('.js-username-field').val('{0}');".format(username))
    browser.execute_script("$('.js-password-field').val('{0}');".format(password))
    browser.find_by_css("button[type='submit'].submit.btn.primary-btn").click()

    if "https://twitter.com/login/error" in browser.url:
        print "The email and password you entered did not match our records."
    else:
        try:
            file = open(txt, 'r')
        except:
            sys.exit("Unable to open file {0}".format(txt))

        preCounter = 0
        for line in file:
            preCounter += 1
        file.close()

        file = open(txt, 'r')
        percent = 0.0
        counter = 0
        for line in file:
            if program:
                try:
                    url_r = re.match(r"(?:https:\/\/)?(?:http:\/\/)?(?:www\.)?twitter\.com/(#!/)?@?([^/\s]*)(/user\?user_id=\d+)?", line.strip())
                    url = url_r.group()
                    browser.visit(url)
                    is_suspended = browser.is_element_present_by_css('.route-account_suspended')
                    if url_r.lastindex == 3 and not is_suspended:
                            browser.find_by_id('ft').find_by_css('.alternate-context').click()
                    if not is_suspended:
                        browser.find_by_css('.user-dropdown').click()
                        browser.find_by_css('li.report-text button[type="button"]').click()
                        with browser.get_iframe('new-report-flow-frame') as iframe:
                            iframe.find_by_css("input[type='radio'][value='abuse']").check()
                        browser.find_by_css('.new-report-flow-next-button').click()
                        with browser.get_iframe('new-report-flow-frame') as iframe:
                            iframe.find_by_css("input[type='radio'][value='harassment']").check()
                        browser.find_by_css('.new-report-flow-next-button').click()
                        with browser.get_iframe('new-report-flow-frame') as iframe:
                            iframe.find_by_css("input[type='radio'][value='Someone_else']").check()
                        browser.find_by_css('.new-report-flow-next-button').click()
                        with browser.get_iframe('new-report-flow-frame') as iframe:
                            iframe.find_by_css("input[type='radio'][value='violence']").check()
                        browser.find_by_css('.new-report-flow-next-button').click()

                        percent = (float(counter+1)/preCounter)*100
                        percent = "%.1f" % percent

                        followers = browser.find_by_css('.ProfileNav-item--followers .ProfileNav-value').first.text
                        user_id = browser.find_by_css("div[data-user-id].ProfileNav").first['data-user-id']

                        twitter_name = url_r.group(2)

                        if 'intent' in twitter_name:
                            twitter_name = browser.find_by_css('.ProfileCardMini-screenname .u-linkComplex-target').first.text

                        msg = "{0} - {1}%: https://twitter.com/intent/user?user_id={2} - {3} - {4} Followers".format(username, percent, user_id, twitter_name, followers)

                        with open("log_reported_"+date+".txt", "a") as log:
                            log.write(msg+"\n")
                    elif browser.is_element_present_by_css('.route-account_suspended'):
                        msg = '{0} - {1}: '.format(username, percent)+line.strip()+' - Suspended'
                        with open("log_suspended.txt", "a") as log:
                            log.write(msg+"\n")
                    else:
                        msg = '{0} - {1}: '.format(username, percent)+line.strip()+' - Unknown'
                        with open("log_unknown.txt", "a") as log:
                            log.write(msg+"\n")

                    print msg

                except HttpResponseError as e:
                    msg = '{0}: {1} - {2}'.format(username, line.strip(), e)
                    print msg
                    with open("log_Error.txt", "a") as log:
                        log.write(msg+"\n")
                except:
                    if line:
                        msg = '{0}: {1} - Error'.format(username, line.strip())
                        print msg
                        with open("log_Error.txt", "a") as log:
                            log.write(msg+"\n")
                    else:
                        pass

                counter += 1
        browser.quit()
        print "{0}: Finished.".format(username)

    activeThreads -= 1

if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except KeyboardInterrupt:
        sys.stdout.write('\nQuit by keyboard interrupt sequence!\n')
