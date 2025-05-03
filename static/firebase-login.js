'use strict';

//import firebase
import { initializeApp } from "https://www.gstatic.com/firebasejs/11.4.0/firebase-app.js";
import { getAuth, createUserWithEmailAndPassword, signInWithEmailAndPassword, signOut } from "https://www.gstatic.com/firebasejs/11.4.0/firebase-auth.js"

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "your-api-key",
  authDomain: "your-auth-domain",
  projectId: "your-project-id",
  storageBucket: "your-storage-bucket",
  messagingSenderId: "your-messaging-sender-id",
  appId: "your-app-id"
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

window.addEventListener("load", function () {
  updateUI(document.cookie);

  // Handle form submission
  const loginForm = document.getElementById("login");
  if (loginForm) {
    loginForm.addEventListener("click", function(e) {
      e.preventDefault();
      handleLogin();
    });
  }

  // Handle signup link click
  const signUpLink = document.getElementById("sign-up");
  if (signUpLink) {
    signUpLink.addEventListener('click', function (e) {
      e.preventDefault();
      handleSignUp();
    });
  }

  // Handle sign out button click
  const signOutButton = document.getElementById("logged-out");
  if (signOutButton) {
    signOutButton.addEventListener('click', function() {
      handleSignOut();
    });
  }
});

// Handle login
function handleLogin() {
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;

  signInWithEmailAndPassword(auth, email, password)
    .then((userCredential) => {
      const user = userCredential.user;
      user.getIdToken().then((token) => {
        document.cookie = "token=" + token + ";path=/;SameSite=Strict";
        window.location = "/dashboard";
      });
    })
    .catch((error) => {
      alert("Login failed: " + error.message);
    });
}

// Handle signup
function handleSignUp() {
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;

  createUserWithEmailAndPassword(auth, email, password)
    .then((userCredential) => {
      const user = userCredential.user;
      
      // Create user document in Firestore
      fetch('/create-user', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          uid: user.uid,
          email: user.email
        })
      });

      user.getIdToken().then((token) => {
        document.cookie = "token=" + token + ";path=/;SameSite=Strict";
        window.location = "/dashboard";
      });
    })
    .catch((error) => {
      alert("Signup failed: " + error.message);
    });
}

// Handle sign out
function handleSignOut() {
  signOut(auth)
    .then(() => {
      document.cookie = "token=;path=/;SameSite=Strict";
      window.location = "/dashboard";
    })
    .catch((error) => {
      alert("Sign out failed: " + error.message);
    });
}

// Update UI based on authentication state
function updateUI(cookie) {
  const token = parseCookieToken(cookie);
  const loginBox = document.getElementById("login-box");

  if (token.length > 0) {
    if (loginBox) loginBox.hidden = true;
  } else {
    if (loginBox) loginBox.hidden = false;
  }
}

// Parse token from cookie
function parseCookieToken(cookie) {
  const strings = cookie.split(';');
  for (let i = 0; i < strings.length; i++) {
    const temp = strings[i].split('=');
    if (temp[0].trim() === "token") {
      return temp[1];
    }
  }
  return "";
}