
const main = document.getElementById("main");
const chat = document.getElementById("chat");
const inputText = document.getElementById("inputText");
const recordButton = document.getElementById('record');
const mute = document.getElementById('mute');
const punctuationRegex = /[.?!]/;
const playbackQueue = [];
const recognition = new window.webkitSpeechRecognition();
let timerId = null;
let muted = false;
let recognizing = false;
let utterance = null;


mute.addEventListener('click', function () {
    if (muted) {
        mute.textContent = "🔇 Enable text to speech";
        mute.title = "Enable text to speech.";
        muted = false;
    } else {
        mute.textContent = "🔈 Disable text to speech";
        mute.title = "Disable text to speech.";
        muted = true;
    }
});


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
    const result = event.results[event.resultIndex][0].transcript;
    inputText.value = result;

    if (timerId) {
        clearTimeout(timerId);
    }
    if (utterance !== null) {
        window.speechSynthesis.cancel();
        utterance = null;
    }
    timerId = setTimeout(() => {
        timerId = null;
        submitChat();
    }, 1500);
};


function start_recognition() {
    if (recognizing) {
        recognition.stop();
        recordButton.textContent = "👂 Enable speech recognition";
        recordButton.setAttribute("aria-label", "record");
        recordButton.title = "Enable speech recognition.";
        recognizing = false;
        return;
    }

    recognition.start();
    recordButton.textContent = "🛑 Disable speech recognition";
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
    main.insertBefore(userChatDiv, main.lastElementChild);

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
                main.appendChild(eventDataDiv);
                eventDataDiv.scrollIntoView();
                inputText.focus();
            } else {
                if (result.content.title) {
                    document.title = result.content.title;
                    //console.log(result.content.title);
                }
                unspoken += result.content.text;
                if (!muted) {
                    if ('speechSynthesis' in window) {
                        utterance = new SpeechSynthesisUtterance();
                        utterance.text = result.content.text;
                        window.speechSynthesis.speak(utterance);

                        utterance.onend = function () {
                            utterance = null;
                        };
                    } else {
                        //
                    }
                }

                eventDataDiv.dataset.content += result.content.text;
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

