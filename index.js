

const chat = document.getElementById("chat");
const inputText = document.getElementById("inputText");
const recordButton = document.getElementById('record');
const mute = document.getElementById('mute');
const punctuationRegex = /[.?!]/;
const playbackQueue = [];



mute.addEventListener('click', function () {
    if (mute.textContent === "🔈") {
        mute.textContent = "🔇";
        mute.title = "Enable text to speech."
    } else {
        mute.textContent = "🔈";
        mute.title = "Disable text to speech."
    }
});


const recognition = new window.webkitSpeechRecognition();
recognition.continuous = true;
recognition.interimResults = true;

recognition.onstart = function () {
    console.log("Voice recognition started.");
};

recognition.onerror = function (event) {
    console.log("Error occurred: " + event.error);
};

recognition.onend = function () {
    console.log("Voice recognition ended.");
};

recognition.onresult = function (event) {
    const result = event.results[0][0].transcript;
    inputText.value = result;
};


let recognizing = false;


function start_recognition() {
    if (recognizing) {
        recognition.stop();
        recordButton.textContent = "🎙️";
        recordButton.setAttribute("aria-label", "record");
        recordButton.title = "Enable speech recognition.";
        recognizing = false;
        return;
    }

    recognition.start();
    recordButton.textContent = "🛑";
    recordButton.setAttribute("aria-label", "stop");
    recordButton.title = "Disable speech recognition.";
    recognizing = true;
}


recordButton.addEventListener('click', () => {
    start_recognition();
});



async function submitChat() {
    let userChatDiv = document.createElement("div");
    userChatDiv.className = "user-chat";
    userChatDiv.textContent = chat.text.value;
    document.body.insertBefore(userChatDiv, document.body.lastElementChild);

    const response = await fetch(chat.action, {
        method: "POST",
        body: new FormData(chat)
    });

    if (response.ok) {
        console.log("Form submitted successfully!");
        chat.text.value = "";

    } else {
        console.error("Form submission failed!");
    }
}


chat.onsubmit = (event) => {
    event.preventDefault();
    submitChat();
};


async function postConversation() {
    const eventSource = new EventSource("conversation");
    let eventDataDiv = document.getElementById("event-data");
    let firstMessage = true;
    let unspoken = "";
    eventSource.onmessage = function(event) {
        if (firstMessage) {
            const result = JSON.parse(event.data);
            chat.action += result.id;
            firstMessage = false;
            eventDataDiv.dataset.content = "";
        } else {
            const result = JSON.parse(event.data);
            if (result.finish_reason) {
                eventDataDiv.id = "";
                eventDataDiv = document.createElement("div");
                eventDataDiv.id = "event-data";
                eventDataDiv.dataset.content = "";
                document.body.appendChild(eventDataDiv);
            } else {
                unspoken += result.content;
                if (mute.textContent === "🔈") {
                    if ('speechSynthesis' in window) {
                        const utterance = new SpeechSynthesisUtterance();
                        utterance.text = result.content;
                        window.speechSynthesis.speak(utterance);
                    } else {
                        //
                    }
                }

                eventDataDiv.dataset.content += result.content;
                eventDataDiv.innerHTML = marked.parse(
                    eventDataDiv.dataset.content
                );
            }

            if (!event.data.length) {
                //console.log("close");
                //eventSource.close();
            }
        }
    };
}


window.onload = postConversation;

