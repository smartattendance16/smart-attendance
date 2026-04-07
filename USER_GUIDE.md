# Smart Attendance System - User Guide for Colleges

## Table of Contents
1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [For College Administrators](#for-college-administrators)
4. [For Students](#for-students)
5. [System Features](#system-features)
6. [Troubleshooting](#troubleshooting)

---

## Overview

The **Smart Attendance System** is a web-based application that uses face recognition technology to automatically mark attendance. This guide covers how to use the system as a college administrator or student.

### Key Features
- ✅ Real-time face recognition for attendance marking
- ✅ Student self-registration with admin approval
- ✅ Comprehensive attendance reports and data export
- ✅ Multi-admin access with role management
- ✅ Secure login with OTP-based password recovery
- ✅ Mobile-responsive web interface

---

## Getting Started

### Accessing the System

The Smart Attendance System is accessible through a web browser at:
```
http://[YOUR_COLLEGE_DOMAIN]/
```

**Browser Requirements:**
- Chrome, Firefox, Safari, or Edge (latest versions recommended)
- JavaScript enabled
- Webcam access (for attendance marking)

### Homepage

When you first visit the system, you'll see the homepage with options to:
1. **Login** (for administrators)
2. **Self-Register** (for new students)

---

## For College Administrators

### 1. Logging In

#### First-Time Administrator Login

1. Navigate to the **Login** page
2. Enter your **username** and **password**
3. Click **Login**

**Note:** Your admin account must be created by the system administrator.

#### Forgot Password?

If you forget your password:
1. Click **Forgot Password?** on the login page
2. Enter your **username**
3. Click **Send OTP**
4. Check your registered **email** for a 6-digit OTP
5. Enter the OTP on the verification page
6. Set your **new password**
7. Log in with your new password

### 2. Dashboard Overview

After logging in, you'll see the **Admin Dashboard** with:

- **Summary Statistics:** Total students, approved registrations, pending approvals
- **Recent Activity:** Latest attendance records and registrations
- **Quick Links:** Navigate to all major features

#### Dashboard Metrics

| Metric | Description |
|--------|-------------|
| **Total Students** | Number of registered, approved students |
| **Pending Approvals** | Student self-registration requests awaiting approval |
| **Today's Attendance** | Number of students marked present today |

### 3. Student Registration & Management

#### Registering Students Manually

**For Administrative Registration (offline/bulk):**

1. From the dashboard, navigate to **Dashboard** → **Register Student**
2. Enter student details:
   - **Roll Number** (unique identifier)
   - **Name** (full name)
   - **Department** (select from dropdown)
   - **Email** (for notifications)
3. Upload **at least 3 photos** of the student from different angles/lighting:
   - Click **Add Photo**
   - Select a clear photo of the student's face
   - Repeat for multiple photos (recommended: 3-5 photos)
4. Click **Register Student**
5. The system will process the photos and create facial encodings
6. Student appears in the student list immediately

**Best Practices for Photos:**
- Ensure faces are clearly visible (front-facing preferred)
- Vary lighting conditions and angles
- Use good quality images (minimum 200x200 pixels)
- Avoid sunglasses, hats, or heavy makeup variations

#### Viewing Registered Students

1. Go to **Dashboard** → **View All Students**
2. You'll see a list of all registered students with:
   - Roll Number
   - Name
   - Department
   - Email
   - Action buttons (View/Edit/Delete)

#### Deleting a Student

1. Go to **View All Students**
2. Find the student record
3. Click **Delete** button
4. Confirm deletion

**Note:** This removes the student's facial encoding and attendance records.

#### Editing Student Information

1. Go to **View All Students**
2. Click **Edit** next to the student
3. Modify information as needed
4. Click **Save Changes**

### 4. Recording Attendance

#### Starting the Attendance Camera

1. From the dashboard, click **Start Attendance** or navigate to **Camera**
2. You'll see:
   - Live video feed from the webcam
   - Detected faces highlighted with green boxes
   - Student names and match percentage when recognized
3. The system automatically marks recognized students as present
4. Click **Stop Attendance** to end the session

#### During Live Attendance

- **Green Box + Green Frame:** Student recognized and marked present
- **Red Box + Red Frame:** Face detected but not recognized (not registered)
- **Yellow Box:** Face detected but processing

**Important Notes:**
- Each student can be marked present only once per day (duplicate prevention)
- The system requires good lighting for accurate recognition
- Students should look directly at the camera for best results
- Attendance is recorded with timestamp

#### Tips for Accurate Attendance

1. **Lighting:** Ensure adequate room lighting; avoid backlighting
2. **Distance:** Students should be 0.5 - 2 meters from the camera
3. **Face Position:** Face should be clearly visible (not partially obscured)
4. **Camera Angle:** Position camera at eye level for best recognition
5. **Time:** Allow 2-3 seconds per student for processing
6. **One at a Time:** Process students one by one for better accuracy

#### Attendance Data Storage

- Attendance records are automatically saved to a CSV file with timestamp
- File format: `attendance_YYYY-MM-DD.csv`
- Location: Stored in the system database

### 5. Viewing Attendance Reports

#### Daily Report

1. Go to **Navigation Menu** → **Report**
2. Select the **Date** from the calendar
3. View students marked present that day:
   - Roll Number
   - Name
   - Department
   - Timestamp of marking
4. View summary: Total present, total registered, attendance percentage

#### Custom Date Range Report

1. Go to **Report**
2. Select **Start Date** and **End Date**
3. Optionally filter by **Department**
4. Click **Generate Report**
5. View:
   - Daily attendance summary
   - Student-wise attendance count
   - Department-wise statistics

#### Report Details Include

- **Student Information:** Roll number, name, department
- **Attendance Count:** How many days attended in the period
- **Attendance Percentage:** (Days Present / Total Days) × 100
- **Dates Present:** List of dates when student was marked present

### 6. Exporting Data

#### Export to CSV Format

1. Go to **Report**
2. Set your desired date range and filters
3. Click **Export as CSV**
4. The file will download automatically as `attendance_report.csv`
5. Open in Excel or any spreadsheet application

#### Export to Excel Format

1. Go to **Report**
2. Set your desired date range and filters
3. Click **Export as Excel**
4. The file will download as `attendance_report.xlsx`
5. Includes multiple sheets for different views

#### CSV Export Structure

```
Roll Number, Name, Department, Date1, Date2, Date3, ... , Attendance %
24B001, John Doe, CSE, Present, Present, Absent, ... , 95%
24B002, Jane Smith, CSE, Present, Absent, Present, ... , 90%
```

#### Excel Export Features

- Sheet 1: Summary (total students, total days, avg attendance)
- Sheet 2: Student-wise attendance (detailed day-by-day)
- Sheet 3: Department statistics
- Formatted with colors and borders for easy reading

### 7. Managing Student Self-Registrations

#### What are Self-Registrations?

Students can register themselves through the **Self-Register** portal and submit their request for approval by administrators.

#### Approving Self-Registration Requests

1. Go to **Dashboard** → **Approvals** (or click pending approvals count)
2. You'll see a list of pending registration requests with:
   - Student's Roll Number
   - Name
   - Email
   - Department
   - Submitted photos
   - Submission date
3. For each request:
   - **View Photos:** Click to preview the submitted photos
   - **Approve:** Click **✓ Approve** to register the student
   - **Reject:** Click **✗ Reject** to decline the registration

#### Approving a Student

1. Click **Approve** on the registration request
2. The system will:
   - Process the student's photos
   - Create facial encodings
   - Add student to the active database
   - Send a confirmation email to the student
3. Student is now ready for attendance marking

#### Rejecting a Student

1. Click **Reject** on the registration request
2. Optionally add a **rejection reason** (will be emailed to student)
3. Click **Confirm Rejection**
4. The request is removed from the pending list
5. Rejection email is sent to the student

**Note:** Rejected students can resubmit their registration request.

#### View All Approvals History

- Go to **Approvals** page
- You can see both pending and completed approvals
- Filter by date range to see historical approvals

### 8. Settings & Admin Management

#### Accessing Settings

1. Click **Settings** from the main menu
2. You'll see options for:
   - Admin management
   - System configuration

#### Adding a New Administrator

1. Go to **Settings**
2. Scroll to **Add New Administrator** section
3. Enter:
   - **Username** (unique login name)
   - **Email** (for OTP recovery)
   - Click **Add Admin**
4. A temporary password is generated and shown
5. Share credentials with the new admin
6. New admin can change password on first login

#### Managing Existing Administrators

1. Go to **Settings**
2. View list of all administrators with:
   - Username
   - Email
   - Action buttons

#### Resetting Administrator Password

1. Go to **Settings**
2. Find the administrator in the list
3. Click **Reset Password**
4. A new temporary password is generated
5. Share with the administrator (they'll need to change it after login)

#### Deleting an Administrator

1. Go to **Settings**
2. Find the administrator to delete
3. Click **Delete**
4. Confirm deletion
5. That admin account is removed and cannot log in

**Warning:** The primary administrator account cannot be deleted.

#### Changing Your Password

1. From any page, click your **username** in the top-right corner
2. Click **Change Password**
3. Enter:
   - **Current Password**
   - **New Password**
   - **Confirm New Password**
4. Click **Update**

### 9. Dashboard Navigation Guide

| Menu Item | Description | Actions |
|-----------|-------------|---------|
| **Dashboard** | Main admin panel | View summary, quick stats |
| **Register** | Add new students manually | Register, view, edit, delete students |
| **Camera** | Real-time attendance marking | Start/stop attendance, view live feed |
| **Report** | View attendance records | Generate reports, view by date/range |
| **Export** | Download attendance data | Export to CSV or Excel |
| **Approvals** | Manage student registrations | Approve/reject self-registered students |
| **Settings** | System & admin management | Add/remove admins, reset passwords |

---

## For Students

### 1. Student Self-Registration

#### When to Self-Register

- If you're a new student and not yet registered in the system
- When your administrator asks you to self-register

#### How to Self-Register

1. Go to the system homepage
2. Click **Self-Register**
3. Enter your details:
   - **Roll Number** (your student ID)
   - **Name** (full name as per records)
   - **Email** (personal email for communication)
   - **Department** (select your department)
4. Upload **at least 3 clear photos** of your face:
   - Click **Add Photo**
   - Select a photo from your device
   - Ensure your face is clearly visible (front-facing)
   - Repeat 3-5 times from different angles/lighting
5. Click **Submit Registration**
6. You'll see: "Registration submitted for approval"
7. Wait for administrator approval (usually within 24-48 hours)
8. Check your email for confirmation

#### Photo Requirements for Self-Registration

- **Quality:** Clear, well-lit photos (minimum 200x200 pixels)
- **Angles:** Vary the angle and lighting (frontal, side profiles)
- **Number:** At least 3 photos, ideally 5
- **Format:** JPG, PNG, or BMP
- **Restrictions:** No sunglasses, hats, or heavy accessories

#### After Approval

Once an administrator approves your registration:
1. You'll receive a confirmation email
2. Your account is activated
3. You can now be marked present using the camera
4. Check attendance using the system

### 2. Checking Your Attendance

#### Viewing Your Attendance

If the system has a student attendance view:
1. Log in with your student credentials (if enabled)
2. Go to **My Attendance**
3. View your attendance record:
   - Dates marked present
   - Attendance percentage
   - Any absences

#### Attendance Marking

- You don't need to do anything! Attendance is marked automatically
- Just stand in front of the camera during the attendance session
- The system recognizes your face and marks you present
- Once marked for the day, you cannot be marked again

### 3. Student Contact Information

If you have issues with your registration or attendance:
- Contact your **department administrator**
- Email the **system administrator**
- Check for updates on the system homepage

---

## System Features

### Real-Time Face Recognition

- **Technology:** Deep learning-based facial encoding (dlib)
- **Speed:** Processes faces in real-time at 30 FPS
- **Accuracy:** 99%+ accuracy with multiple clear photos
- **Database:** Stores 128-dimensional face encodings for comparison

### Automated Duplicate Prevention

- Each student can be marked present only once per day
- The system logs timestamp of attendance marking
- Multiple scan attempts from the same face are ignored

### Data Security

- **Password Hashing:** Secure scrypt-based password hashing
- **Session Management:** Secure session-based authentication
- **OTP Verification:** 6-digit OTP sent via email for password recovery
- **Database Encryption:** Sensitive data encrypted at rest

### Data Backup & Export

- Daily attendance records automatically saved
- Export functionality for CSV and Excel formats
- Backup files stored securely on the server
- Historical data retention for audit purposes

### Multi-Admin Support

- Multiple administrators can access the system simultaneously
- Role-based access control
- Admin action logging for audit trail
- Password reset and account management

---

## Troubleshooting

### Common Issues & Solutions

#### 1. **Face Not Being Recognized**

**Problem:** Student is standing in front of camera but not being recognized.

**Solutions:**
- **Improve Lighting:** Ensure adequate room lighting; avoid backlighting
- **Clear Face:** Remove sunglasses, hats, masks, or heavy makeup
- **Camera Distance:** Move student 0.5-2 meters from camera
- **Re-register:** Request administrator to re-register with better photos
- **Try Again:** Wait 5 seconds and try again; poor angle may have caused failure

#### 2. **"Face Detected but Not Recognized"**

**Problem:** Red box appears around face but name doesn't show.

**Solutions:**
- Student may not be registered yet
- Student photo registration was not successful
- Face angle or lighting is too different from registration photos
- Contact administrator to verify student is registered

#### 3. **Camera Not Working**

**Problem:** "Camera not accessible" or black video feed.

**Solutions:**
- Check browser camera permissions (need to allow on first use)
- Ensure webcam is connected and functional
- Try refreshing the page
- Close other applications using the camera
- Check browser console for errors (F12 → Console)

#### 4. **Cannot Login**

**Problem:** Username/password not working.

**Solutions:**
- **Verify Username:** Check spelling and capitalization
- **Caps Lock:** Ensure Caps Lock is off
- **Forgot Password:** Click "Forgot Password?" to reset
- **Cookies:** Clear browser cookies and try again
- **Contact Admin:** Ask system administrator to reset your password

#### 5. **OTP Not Received**

**Problem:** "Didn't receive OTP code" email.

**Solutions:**
- **Check Spam:** Look in email spam/junk folder
- **Wait:** Sometimes emails take 1-2 minutes to arrive
- **Email Address:** Verify your email address is correct in the system
- **Resend:** Click "Resend OTP" to send a new code
- **Contact Admin:** If problem persists, contact administrator

#### 6. **Attendance Not Recorded**

**Problem:** Student was in front of camera but not marked present.

**Solutions:**
- **Already Marked:** Check if student was already marked present today
- **Poor Recognition:** Face may not have been recognized (see #1)
- **User Error:** Attendance marking session may have been stopped
- **Check Report:** Verify in reports if attendance was actually recorded
- **Manual Entry:** Administrator can manually add attendance if needed

#### 7. **Slow Performance / Lag**

**Problem:** System is slow or attendance marking is lagging.

**Solutions:**
- **Browser:** Close other tabs and applications
- **Internet:** Check internet connection speed
- **Camera:** Use USB 2.0 or better; check camera quality
- **System Load:** Wait during off-peak hours
- **Refresh:** Reload the page to clear memory

#### 8. **Self-Registration Rejected**

**Problem:** Your self-registration was rejected.

**Solutions:**
- **Check Email:** Read rejection reason in the email notification
- **Photo Quality:** Re-register with clearer, well-lit photos
- **Information:** Verify all entered information is correct
- **Duplicate:** Check if you're already registered in the system
- **Contact Admin:** Ask administrator why it was rejected

#### 9. **Cannot Export Report**

**Problem:** Export button doesn't work or download fails.

**Solutions:**
- **Browser:**Enable pop-ups and downloads in browser settings
- **File Size:** If period is long, try shorter date range
- **Format:** Try different format (CSV vs Excel)
- **Refresh:** Reload the page and try again
- **Storage:** Ensure your device has free disk space

#### 10. **"Connection Error" or "Server Offline"**

**Problem:** System shows connection error.

**Solutions:**
- **Internet:** Check your internet connection
- **Server Status:** System may be temporarily down for maintenance
- **Try Later:** Wait a few minutes and refresh
- **URL:** Verify you're using the correct system URL
- **Contact Admin:** Check with IT/system administrator

### Getting Help

If you encounter an issue not listed above:

1. **Take a Screenshot:** Capture the error message
2. **Note the Time:** Record when the problem occurred
3. **Browser Info:** Check browser version (Chrome, Firefox, etc.)
4. **Details:** Write down step-by-step what you were doing
5. **Contact:** Email/call your system administrator with this information

### System Administrator Contact

**Email:** [IT Department Email]  
**Phone:** [IT Support Phone]  
**Support Hours:** [Hours of Operation]

---

## General Tips & Best Practices

### For Administrators

1. **Regular Backups:** Export attendance data weekly for backup
2. **Review Reports:** Check reports regularly for anomalies
3. **Update Passwords:** Change your admin password monthly
4. **Manage Admins:** Remove unused admin accounts regularly
5. **Clean Data:** Delete graduated students from the system
6. **Monitor Queue:** Check pending approvals daily
7. **Lighting:** Keep camera area well-lit
8. **Camera Position:** Mount camera at eye level, stable position

### For Students

1. **Complete Registration:** Register early in the semester
2. **Quality Photos:** Submit clear photos with good lighting
3. **Be On Time:** Arrive during attendance marking time
4. **Face Clearly:** Look directly at camera, uncovered face
5. **Check Status:** Verify you've been marked present after session
6. **Report Issues:** Immediately notify if you weren't marked present
7. **Update Info:** Inform admin of major appearance changes

### System Best Practices

1. **Regular Maintenance:** Schedule system maintenance during off-hours
2. **Monitor Accuracy:** Periodically review attendance for errors
3. **Disk Space:** Monitor free disk space for database and archives
4. **Security Updates:** Keep system and software updated
5. **Database Backups:** Daily automated backups recommended
6. **Audit Logging:** Review admin activity logs monthly

---

## Keyboard Shortcuts

While in the camera/attendance view:
- **ESC:** Exit full-screen or back to menu
- **SPACE:** Pause/resume live feed (if available)
- **R:** Refresh camera feed
- **Q:** Quit/stop attendance session

---

## System Requirements & Browser Compatibility

| Component | Requirement |
|-----------|-------------|
| **Operating System** | Windows, macOS, or Linux |
| **Browser** | Chrome 90+, Firefox 88+, Safari 14+, Edge 90+ |
| **Internet** | Stable connection (minimum 2 Mbps) |
| **Webcam** | 720p or higher resolution |
| **RAM** | 2 GB minimum (4 GB recommended) |
| **Storage** | 100 MB free space (varies by data size) |

---

## FAQ - Frequently Asked Questions

**Q1: How many students can the system handle?**  
A: The system can handle thousands of students. Performance depends on server resources and the number of photos per student.

**Q2: What's the accuracy of face recognition?**  
A: With good quality photos and lighting, accuracy is 99%+. Real-world conditions may vary.

**Q3: Can I mark attendance manually if the camera fails?**  
A: Contact your system administrator. Manual entry may be possible through the database.

**Q4: How long are attendance records kept?**  
A: Records are kept indefinitely unless the administrator deletes them or the student is removed.

**Q5: Can students access their own attendance?**  
A: This depends on system configuration. Contact your administrator to enable student self-service access.

**Q6: What if a student changes their appearance significantly?**  
A: Re-register the student with new photos. The system allows updating facial encodings.

**Q7: Is the system mobile-friendly?**  
A: Yes, the system is responsive (works on phones and tablets), but attendance marking requires a webcam (desktop/laptop).

**Q8: Can I integrate this with my college's existing database?**  
A: Contact your system administrator about integration possibilities.

---

## Document Information

- **Version:** 2.0
- **Last Updated:** April 2026
- **Applicable System Version:** Smart Attendance System v2.0+

For the latest updates or additional help, contact your college's IT department or system administrator.

---

*Thank you for using the Smart Attendance System!*
