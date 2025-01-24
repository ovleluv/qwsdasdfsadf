
// 채팅 메시지를 추가하는 함수
function appendMessage(message, sender) {
    const chatBox = document.getElementById('chat-box');
    const messageDiv = document.createElement('div');
    messageDiv.className = sender === 'bot' ? 'bot-message' : 'user-message';

    messageDiv.textContent = message;
    chatBox.appendChild(messageDiv);

    // 메시지 간 간격 유지 및 정렬 보장
    chatBox.appendChild(document.createElement('br'));

    // 자동 스크롤
    chatBox.scrollTop = chatBox.scrollHeight;
}

// 계약서 선택 시 처리하는 함수
function selectContract(selection) {
    let contractName = '';
    if (selection === '1') contractName = '부동산임대차계약서';
    else if (selection === '2') contractName = '위임장';
    else if (selection === '3') contractName = '소장';

    appendMessage(`선택: ${contractName}`, 'user');

    // 계약서 종류 선택 처리
    fetch('/select', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ selection: selection })
    })
    .then(response => response.json())
    .then(data => {
        appendMessage(data.message, 'bot');

        // 계약서 내용 생성 요청
        generateContractContent(selection);
    })
    .catch(() => {
        appendMessage('서버 오류가 발생했습니다. 다시 시도해주세요.', 'bot');
    });

    document.getElementById('button-options').style.display = 'none';
    document.getElementById('user-input').style.display = 'block';
}

// GPT API를 통해 계약서 내용을 생성하는 함수
function generateContractContent(selection) {
    appendMessage("계약서를 생성 중입니다. 잠시만 기다려 주세요...", 'bot');

    // localStorage에서 저장된 필드 데이터 가져오기
    const extractedFields = localStorage.getItem('extracted_fields');
    const requestData = {
        selection: selection,
        extracted_fields: extractedFields ? JSON.parse(extractedFields) : {}
    };

    fetch('/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.contract) {
            currentContract = data.contract;  // 계약서 내용 저장
            appendMessage("생성된 계약서를 확인해 주세요:\n\n" + data.contract, 'bot');
            requestInputFields(selection);
        } else {
            appendMessage("계약서 생성에 실패했습니다. 다시 시도해 주세요.", 'bot');
        }
    })
    .catch(() => {
        appendMessage("서버 오류가 발생했습니다. 다시 시도해 주세요.", 'bot');
    });
}

// 계약서 업데이트 후 버튼 추가
function updateContract(extractedFields) {
    if (!currentContract) {
        console.error("현재 계약서 내용이 없습니다.");
        return;
    }

    appendMessage("계약서를 업데이트하는 중입니다...", 'bot');

    fetch('/update-contract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            current_contract: currentContract,
            extracted_fields: extractedFields
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.contract) {
            currentContract = data.contract;  // 업데이트된 계약서 내용 저장
            appendMessage("업데이트된 계약서 내용입니다:\n\n" + data.contract, 'bot');
            addDownloadButton();  // 다운로드 버튼 추가
        } else {
            appendMessage("계약서 업데이트에 실패했습니다.", 'bot');
        }
    })
    .catch(() => {
        appendMessage("서버 오류가 발생했습니다.", 'bot');
    });
}


// 사용자 입력이 필요한 항목 요청 함수
function requestInputFields(selection) {
    appendMessage("작성에 필요한 항목을 확인 중입니다...", 'bot');

    fetch('/input-fields', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ selection: selection })
    })
    .then(response => response.json())
    .then(data => {
        if (data.message) {
            appendMessage(data.message, 'bot');
        } else {
            appendMessage("입력 항목 요청에 실패했습니다. 다시 시도해 주세요.", 'bot');
        }
    })
    .catch(() => {
        appendMessage("서버 오류가 발생했습니다. 다시 시도해 주세요.", 'bot');
    });
}

// 사용자가 입력한 문장을 분석하는 함수
function extractContractFields(userInput) {
    console.log("[DEBUG] extractContractFields 호출됨, 사용자 입력:", userInput);

    appendMessage("입력 내용을 분석 중입니다...", 'bot');

    fetch('/extract-fields', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_input: userInput })
    })
    .then(response => response.json())
    .then(data => {
        console.log("[DEBUG] 서버 응답:", data);

        if (data.extracted_fields) {
            let extracted;
            try {
                extracted = JSON.parse(data.extracted_fields);

                // 추출된 필드 데이터 저장
                localStorage.setItem('extracted_fields', JSON.stringify(extracted));

                let resultMessage = "다음과 같은 항목이 추출되었습니다:\n\n";
                for (const [key, value] of Object.entries(extracted)) {
                    if (typeof value === 'object') {
                        resultMessage += `- ${key}: ${JSON.stringify(value)}\n`;
                    } else {
                        resultMessage += `- ${key}: ${value}\n`;
                    }
                }
                appendMessage(resultMessage, 'bot');

                // 추출된 데이터로 계약서 업데이트
                updateContract(extracted);
            } catch (error) {
                console.error("[ERROR] JSON 파싱 실패:", error);
                appendMessage("응답 데이터 파싱에 실패했습니다.", 'bot');
            }
        } else if (data.error) {
            appendMessage("서버 오류: " + data.error, 'bot');
        } else {
            appendMessage("항목 추출에 실패했습니다. 다시 시도해 주세요.", 'bot');
        }
    })
    .catch((error) => {
        console.error("[ERROR] 요청 실패:", error);
        appendMessage("서버 오류가 발생했습니다. 다시 시도해 주세요.", 'bot');
    });
}

// 사용자 입력 전송 버튼 클릭 이벤트
document.getElementById('send-btn').addEventListener('click', function () {
    const message = document.getElementById('text-input').value.trim();

    if (message === '') return; // 빈 메시지 방지

    appendMessage(message, 'user'); // 사용자 메시지 추가
    document.getElementById('text-input').value = ''; // 입력 필드 초기화

    // ✅ 입력값을 extractContractFields로 전달
    extractContractFields(message);
});

// 사용자 엔터 키 입력 시 전송
document.getElementById('text-input').addEventListener('keypress', function (event) {
    if(event.key === 'Enter') {
        event.preventDefault(); // 기본 엔터 키 동작 방지
        const message = document.getElementById('text-input').value.trim();

        if (message === '') return; // 빈 메시지 방지

        appendMessage(message, 'user'); // 사용자 메시지 추가
        document.getElementById('text-input').value = ''; // 입력 필드 초기화

        // ✅ 입력값을 extractContractFields로 전달
        extractContractFields(message);
    }
});

// 계약서 다운로드 함수
function downloadContract() {
    fetch('/download', {
        method: 'GET'
    })
    .then(response => {
        if (response.ok) {
            return response.blob();
        } else {
            appendMessage("계약서 파일을 다운로드할 수 없습니다.", 'bot');
        }
    })
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'completed_contract.docx';  // 다운로드 파일명
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    })
    .catch(() => {
        appendMessage("서버 오류가 발생했습니다. 다시 시도해 주세요.", 'bot');
    });
}

// 다운로드 버튼 추가
function addDownloadButton() {
    const downloadButton = document.createElement('button');
    downloadButton.textContent = "계약서 다운로드";
    downloadButton.addEventListener('click', downloadContract);

    const chatBox = document.getElementById('chat-box');
    chatBox.appendChild(document.createElement('br'));
    chatBox.appendChild(downloadButton);
}
