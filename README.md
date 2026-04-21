# ✈️ Airline Seat Reservation System

A web-based Airline Seat Reservation System built using Flask and SQLite. This application allows users to search for flights, book tickets, enter passenger details, and generate tickets.

---

## 🚀 Features

- User Signup & Login Authentication
- Flight Search (Departure, Destination, Date)
- Dynamic Flight Generation
- Passenger Details Form
- Booking System with PNR Generation
- Ticket Viewing
- Basic Seat Selection UI
- Check-in Page
- Boarding Pass Display

---

## 🛠️ Tech Stack

- Backend: Python (Flask)
- Database: SQLite (SQLAlchemy)
- Frontend: HTML (Jinja Templates)
- Security: Password Hashing (Werkzeug)

---

## 📁 Project Structure

```
Airline-Seat-Reservation-system/
│
├── app.py
│
└── templates/
    ├── base.html
    ├── boarding_pass.html
    ├── check_in.html
    ├── flights.html
    ├── home.html
    ├── login.html
    ├── passenger_details.html
    ├── payment.html
    ├── seats.html
    ├── signup.html
    └── ticket.html
```

---

## ⚙️ Installation & Setup

1. Clone the repository

git clone https://github.com/Udaysri2025/airline-seat-reservation-system.git  
cd airline-seat-reservation-system  

2. Create virtual environment

python -m venv venv  
venv\Scripts\activate   (Windows)  
source venv/bin/activate (Linux/Mac)  

3. Install dependencies

pip install flask flask_sqlalchemy werkzeug  

4. Run the application

python app.py  

5. Open in browser

http://127.0.0.1:5000  

---

## 🔑 Test User (if initialized)

Email: test@example.com  
Password: test123  

---

## 🧠 Key Functional Flow

1. User registers or logs in  
2. Searches for flights  
3. Selects flight  
4. Enters passenger details  
5. Proceeds to payment (simulated)  
6. Booking is confirmed with PNR  
7. Ticket is generated and displayed  

---

## 🔐 Security Features

- Password hashing using Werkzeug
- Session-based authentication
- Secure cookies configuration

---

## 📌 Future Improvements

- Real payment gateway integration  
- Email ticket confirmation  
- Advanced seat selection UI  
- Admin dashboard  
- Mobile responsive design  

---

## 📜 License

This project is for educational purposes.

---

## 👨‍💻 Author

Udaysri Yaramati

---

## ⭐ Support

If you like this project, give it a star on GitHub!
