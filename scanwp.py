import argparse
import requests
import threading
import sys
from queue import Queue
from termcolor import colored

putih = '\033[0;37m'
merah = '\033[0;31m'
hijau = '\033[0;32m'
kuning = '\033[0;33m'
biru = '\033[0;34m'
ungu = '\033[0;35m'
reset = '\033[0m'

DEFAULT_THREADS = 60

def print_colored(message, color):
    print(colored(message, color))

def check_url(url, queue, output_file, show_status_code=False):
    try:
        wp_login_response = requests.get(url + '/wp-login.php', timeout=10, allow_redirects=False)
        if wp_login_response.status_code == 200:
            status_code = wp_login_response.status_code
            result = "Found WordPress"
            color = "green"
        elif 300 <= wp_login_response.status_code < 400:
            status_code = wp_login_response.status_code
            result = "Redirected"
            color = "yellow"
        else:
            xmlrpc_response = requests.get(url + '/xmlrpc.php', timeout=10, allow_redirects=False)
            if xmlrpc_response.status_code == 200:
                status_code = xmlrpc_response.status_code
                result = "Found WordPress"
                color = "green"
            elif 300 <= xmlrpc_response.status_code < 400:
                status_code = xmlrpc_response.status_code
                result = "Redirected"
                color = "yellow"
            else:
                status_code = wp_login_response.status_code
                result = "Other"
                color = "red"

        if show_status_code:
            status_msg = f"{kuning}{url}{reset} {putih}>>> {reset}{ungu}[{status_code}]{reset} {colored(result, color)}"
        else:
            status_msg = f"{kuning}{url}{reset} {putih}>>> {reset}{colored(result, color)}"

        print(status_msg)

        if result == "Found WordPress" and output_file:
            output_file.write(f"{url}\n")
    except requests.RequestException:
        print(f"{kuning}{url} {putih}>>> {merah}Other{reset}")
    finally:
        queue.task_done()

def process_queue(queue, output_file, show_status_code):
    while True:
        url = queue.get()
        check_url(url, queue, output_file, show_status_code)

def ensure_http_protocol(url):
    if not url.startswith("http://") and not url.startswith("https://"):
        return "https://" + url
    return url

def main():
    parser = argparse.ArgumentParser(description="Get website who use wordpress cms.")
    parser.add_argument("-u", "--url", help="Single target URL to scan")
    parser.add_argument("-l", "--list", help="File containing list of URLs to scan")
    parser.add_argument("-o", "--output", help="File to save the results")
    parser.add_argument("-t", "--threads", type=int, default=DEFAULT_THREADS, help="Number of threads to use (default: 60)")
    parser.add_argument("-sc", "--status-code", action='store_true', help="Show status codes")

    args = parser.parse_args()

    if not args.url and not args.list:
        parser.print_help()
        sys.exit(1)

    urls = []

    if args.url:
        urls.append(ensure_http_protocol(args.url))

    if args.list:
        try:
            with open(args.list, 'r') as file:
                urls.extend([ensure_http_protocol(line.strip()) for line in file if line.strip()])
        except FileNotFoundError:
            print_colored("File not found", "red")
            sys.exit(1)

    queue = Queue()

    output_file = open(args.output, 'w') if args.output else None

    for _ in range(args.threads):
        worker = threading.Thread(target=process_queue, args=(queue, output_file, args.status_code))
        worker.daemon = True
        worker.start()

    for url in urls:
        queue.put(url)

    queue.join()

    if output_file:
        output_file.close()

    print_colored("Scan complete!", "green")

if __name__ == "__main__":
    main()
