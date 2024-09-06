import argparse
import requests
import threading
import sys
from queue import Queue
from termcolor import colored

# Warna ANSI untuk output
putih = '\033[0;37m'
merah = '\033[0;31m'
hijau = '\033[0;32m'
kuning = '\033[0;33m'
biru = '\033[0;34m'
ungu = '\033[0;35m'
reset = '\033[0m'

# Default thread count
DEFAULT_THREADS = 60

# Function to print messages with color
def print_colored(message, color):
    print(colored(message, color))

# Function to check a single URL
def check_url(url, queue, output_file, show_status_code=False):
    try:
        # Check wp-login.php
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
            # Check xmlrpc.php if wp-login.php not found
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

        # Construct status message
        if show_status_code:
            status_msg = f"{kuning}{url}{reset} {putih}>>> {reset}{ungu}[{status_code}]{reset} {colored(result, color)}"
        else:
            status_msg = f"{kuning}{url}{reset} {putih}>>> {reset}{colored(result, color)}"

        # Print status message
        print(status_msg)

        # Append to results if Found WordPress and not redirected
        if result == "Found WordPress" and output_file:
            output_file.write(f"{url}\n")
    except requests.RequestException:
        print(f"{kuning}{url} {putih}>>> {merah}Other{reset}")
    finally:
        queue.task_done()

# Function to process the queue
def process_queue(queue, output_file, show_status_code):
    while True:
        url = queue.get()
        check_url(url, queue, output_file, show_status_code)

# Function to ensure URL starts with http:// or https://
def ensure_http_protocol(url):
    if not url.startswith("http://") and not url.startswith("https://"):
        return "https://" + url
    return url

# Main function
def main():
    parser = argparse.ArgumentParser(description="Web Target Scanner")
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

    # Open the output file if specified
    output_file = open(args.output, 'w') if args.output else None

    # Start threads
    for _ in range(args.threads):
        worker = threading.Thread(target=process_queue, args=(queue, output_file, args.status_code))
        worker.daemon = True  # Set thread as daemon
        worker.start()

    # Enqueue all URLs
    for url in urls:
        queue.put(url)

    # Wait for all threads to finish
    queue.join()

    # Close the output file if specified
    if output_file:
        output_file.close()

    print_colored("Scan complete!", "green")

if __name__ == "__main__":
    main()
