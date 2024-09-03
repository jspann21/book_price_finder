import sys
import re
import requests
from bs4 import BeautifulSoup
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QGroupBox, QGridLayout, QTableWidget, QTableWidgetItem, QHeaderView
from PyQt5.QtCore import Qt, QThread, pyqtSignal

class BookPriceFinder(QWidget):
    def __init__(self):
        super().__init__()

        # Set window size
        self.setWindowTitle("Book Price Finder")
        self.setGeometry(100, 100, 1200, 800)  # Width: 1200px, Height: 800px

        # Main layout
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        # ISBN entry field
        self.isbn_entry = QLineEdit(self)
        self.isbn_entry.setPlaceholderText("Enter ISBN")
        self.main_layout.addWidget(self.isbn_entry)

        # Search button
        self.search_button = QPushButton("Search Prices", self)
        self.search_button.clicked.connect(self.start_search)
        self.main_layout.addWidget(self.search_button)

        # Results layout
        self.results_layout = QGridLayout()
        self.main_layout.addLayout(self.results_layout)

        # eBay.com results with scrollbar
        self.ebay_group = QGroupBox("eBay.com")
        self.ebay_layout = QVBoxLayout()

        self.ebay_table = QTableWidget(0, 4)  # 4 columns: Date, Title, Price, Shipping
        self.ebay_table.setHorizontalHeaderLabels(["Date", "Title", "Price", "Shipping"])
        self.ebay_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.ebay_table.setStyleSheet("QTableWidget::item { padding: 5px }")
        self.ebay_table.verticalHeader().setVisible(False)
        self.ebay_table.setSizeAdjustPolicy(QTableWidget.AdjustToContents)
        
        self.ebay_layout.addWidget(self.ebay_table)
        self.ebay_group.setLayout(self.ebay_layout)
        self.results_layout.addWidget(self.ebay_group, 0, 0)

        # URLs group box
        self.urls_group = QGroupBox("Manual Links")
        self.urls_layout = QVBoxLayout()

        self.bookfinder_link = QLabel(self)
        self.isbns_link = QLabel(self)
        self.alibris_link = QLabel(self)

        self.urls_layout.addWidget(self.bookfinder_link)
        self.urls_layout.addWidget(self.isbns_link)
        self.urls_layout.addWidget(self.alibris_link)

        self.urls_group.setLayout(self.urls_layout)
        self.results_layout.addWidget(self.urls_group, 1, 0)

        # Log window
        self.log_window = QTextEdit(self)
        self.log_window.setReadOnly(True)
        self.log_window.setFixedHeight(self.height() * 1 // 6)
        self.main_layout.addWidget(self.log_window)

    def log_action(self, message):
        self.log_window.append(message)

    def start_search(self):
        isbn = self.isbn_entry.text().strip()
        cleaned_isbn = re.sub(r'\W+', '', isbn)
        if not cleaned_isbn:
            self.log_action("Invalid ISBN entered.")
            return

        self.log_action(f"Searching prices for ISBN: {cleaned_isbn}")

        # Clear previous results
        self.ebay_table.setRowCount(0)
        self.bookfinder_link.clear()
        self.isbns_link.clear()
        self.alibris_link.clear()

        # Start the search in a separate thread to keep the UI responsive
        self.search_thread = SearchThread(cleaned_isbn)
        self.search_thread.ebay_results.connect(self.display_ebay_results)
        self.search_thread.log_message.connect(self.log_action)
        self.search_thread.url_ready.connect(self.display_urls)
        self.search_thread.start()

    def display_ebay_results(self, results):
        if not results:
            self.ebay_table.insertRow(0)
            self.ebay_table.setItem(0, 0, QTableWidgetItem("No results found on eBay."))
        else:
            for sold_date, title, price, shipping_cost in results:
                row_position = self.ebay_table.rowCount()
                self.ebay_table.insertRow(row_position)
                self.ebay_table.setItem(row_position, 0, QTableWidgetItem(sold_date))
                self.ebay_table.setItem(row_position, 1, QTableWidgetItem(title))
                self.ebay_table.setItem(row_position, 2, QTableWidgetItem(price))
                self.ebay_table.setItem(row_position, 3, QTableWidgetItem(shipping_cost))

    def display_urls(self, urls):
        bookfinder_url, isbns_url, alibris_url = urls
        self.bookfinder_link.setText(f'<a href="{bookfinder_url}" target="_blank">Open BookFinder.com Search</a>')
        self.bookfinder_link.setOpenExternalLinks(True)
        self.isbns_link.setText(f'<a href="{isbns_url}" target="_blank">Open ISBNS.net Search</a>')
        self.isbns_link.setOpenExternalLinks(True)
        self.alibris_link.setText(f'<a href="{alibris_url}" target="_blank">Open Alibris Search</a>')
        self.alibris_link.setOpenExternalLinks(True)


class SearchThread(QThread):
    ebay_results = pyqtSignal(list)
    log_message = pyqtSignal(str)
    url_ready = pyqtSignal(tuple)

    def __init__(self, isbn):
        super().__init__()
        self.isbn = isbn

    def run(self):
        # Perform the eBay search
        ebay_results = self.search_ebay()
        self.ebay_results.emit(ebay_results)

        # Generate URLs for manual search
        bookfinder_url = f"https://www.bookfinder.com/search/?keywords={self.isbn}&currency=USD&destination=us&mode=advanced&il=en&classic=2&ps=tp&lang=en&st=sh&ac=qr&submit="
        isbns_url = f"https://www.isbns.net/isbn/{self.isbn}/?posted=1&used=True&rentals=False&digital=False&variants=False"
        alibris_url = f"https://www.alibris.com/booksearch?mtype=B&keyword={self.isbn}&hs.x=0&hs.y=0"
        self.url_ready.emit((bookfinder_url, isbns_url, alibris_url))

    def search_ebay(self):
        url = f"https://www.ebay.com/sch/i.html?_from=R40&_nkw={self.isbn}&_sacat=0&_nls=2&_dmd=2&rt=nc&LH_Sold=1&LH_Complete=1"
        self.log_message.emit(f"Searching eBay with URL: {url}")
        
        try:
            response = requests.get(url, timeout=30)  # Timeout after 30 seconds
            soup = BeautifulSoup(response.text, 'html.parser')

            result_heading = soup.find('h1', class_='srp-controls__count-heading')

            if not result_heading:
                return []

            results = []
            for item in soup.find_all('div', class_='s-item__info clearfix'):
                title_tag = item.find('div', class_='s-item__title')
                title = title_tag.text if title_tag else ""

                # Skip if the title is "Shop on eBay"
                if title.lower().strip() == "shop on ebay":
                    continue

                sold_date_tag = item.find('span', class_='POSITIVE')
                sold_date = sold_date_tag.text if sold_date_tag else "Unknown Date"

                price = item.find('span', class_='s-item__price').text
                shipping = item.find('span', class_='s-item__shipping')
                shipping_cost = shipping.text if shipping else "No shipping info"

                results.append((sold_date, title, price, shipping_cost))

            self.log_message.emit("Results retrieved from eBay.com.")
            return results

        except requests.Timeout:
            self.log_message.emit("eBay search timed out.")
            return []


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = BookPriceFinder()
    window.show()
    sys.exit(app.exec_())
