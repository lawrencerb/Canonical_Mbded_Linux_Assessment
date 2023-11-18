import requests
import gzip
from bs4 import BeautifulSoup
import argparse
from collections import Counter
import os
import sys

def download_file(url, destination):
    """
    Download the user input file content from the Debian repository.

    Note: This function by default call downloads the file to user's current working directory.
    If permissions are not granted to write to the current working directory, this function will fail.
    """
    try:
        print("Valid input detected, downloading files...")
        # Initiating a GET request to download the file
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code

        # Adding a counter to show progress
        downloaded = 0
        total_size = int(response.headers.get('content-length', 0))

        # Writing the content to a destination file in chunks
        with open(destination, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    downloaded += len(chunk)
                    print(f"Downloaded {downloaded} of {total_size} bytes", end='\r')
        print("\nDownload complete.")
        return True
    except requests.HTTPError as e:
        print(f"HTTP error: {e}")
        return False
    except requests.RequestException as e:
        print(f"Error downloading file: {e}")
        return False

def decompress_gzip(file_path):
    try:
        # Opening the gzip file and writing the decompressed data to a new file
        with gzip.open(file_path, 'rb') as f_in:
            with open(file_path.replace('.gz', ''), 'wb') as f_out:
                f_out.write(f_in.read())
        return True
    except Exception as e:
        print(f"Error decompressing file: {e}")
        return False

def parse_contents_file(file_path):
    """
    Parses the Contents file and counts the number of files associated with each package.

    The function reads the Contents file line by line. Each line consists of a file path and 
    one or more package names. It counts how many times each package appears in the file,
    indicating how many files are associated with that package.

    Args:
        file_path (str): The path to the Contents file.

    Returns:
        list: A list of tuples, each containing a package name and the count of associated files,
              sorted in descending order of the file count.
    """
    package_file_count = Counter()

    with open(file_path, 'r') as file:
        for line in file:
            # Splitting each line into file path and package names
            parts = line.strip().split()
            if len(parts) >= 2:
                packages = parts[1].split(',')
                # Increment the count for each package found on the line
                for package in packages:
                    package_file_count[package] += 1

    # Retrieving the top 10 packages with the most files
    top_packages = package_file_count.most_common(10)

    return top_packages

def analyze_data(file_path):
    """
    Analyzes the Contents file and prints the top 10 packages with the most associated files.

    This function calls parse_contents_file to get the statistics of the file associations
    and then prints the top 10 packages along with the number of files associated with each.

    Args:
        file_path (str): The path to the Contents file.
    """
    top_packages = parse_contents_file(file_path)
    print("\nTop 10 packages with the most files:")
    print(f"{'Index':<6} {'Package Name':<40} {'Number of Files':>15}")
    print("-" * 65)  # Print a separator line

    for index, (package, count) in enumerate(top_packages, start=1):
        print(f"{index:<6} {package:<40} {count:>15}")


def get_supported_architectures(url):
    """
    Retrieves a list of supported architectures from the Debian repository.

    Note: This function assumes a specific structure of the Debian repository page. 
    If the page layout or naming conventions change, this function may require adjustments.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        # Extracting directories which typically represent architectures
        architecture_links = soup.find_all('a')
        architectures = []

        for link in architecture_links:
            href = link.get('href')
            if href.startswith('binary-'):
                arch = href.split('-')[1].rstrip('/')
                if arch != 'all':  # Skip 'all' architecture
                    architectures.append(arch)


        return architectures
    except requests.RequestException as e:
        print(f"Error retrieving architectures: {e}")
        return []

def main(architecture):

    base_url = "http://ftp.uk.debian.org/debian/dists/stable/main/"
    script_directory = os.path.dirname(os.path.realpath(__file__))
    file_name = f"Contents-{architecture}.gz"
    destination = os.path.join(script_directory, file_name)
    decompressed_file = destination.replace('.gz', '')
    url = base_url + file_name

    # [3. Validate Input]
    architectures = get_supported_architectures(base_url)

    if architecture not in architectures:
        sys.exit(f"Error: '{architecture}' is not a supported architecture. Please choose from {', '.join(architectures)}.")

    # Architecture is valid, proceed with the script
    # [4. Download Contents File]
    if not download_file(url, destination):
        sys.exit(f"Failed to download the file: {url}")

    # [5. Decompressing the Contents file]
    if not decompress_gzip(destination):
        sys.exit(f"Failed to decompress the file: {destination}")

    # [6. Parsing and Analyze the decompressed file]
    try:
        analyze_data(decompressed_file)
    finally:
        # Clean up: remove the downloaded and decompressed files
        print("Cleaning up downloaded files")
        if os.path.exists(destination):
            os.remove(destination)
            print(f"Removed downloaded file: {destination}")

        if os.path.exists(decompressed_file):
            os.remove(decompressed_file)
            print(f"Removed decompressed file: {decompressed_file}")

# [1. Start]
if __name__ == "__main__":
    # [2. User Input Argument: Processor Architechture]
    parser = argparse.ArgumentParser(description="Debian Package Statistics Tool")
    parser.add_argument("architecture", help="Processor architecture (e.g., amd64, arm64)")
    args = parser.parse_args()

    # Running the main function with the provided architecture argument
    main(args.architecture)