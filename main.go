package main

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"github.com/gorilla/websocket"
	"net/http"
	"os"
	"strings"
)

type ImageData struct {
	Command   string `json:"command"` //request, upload
	ID        string `json:"id"`
	Base64Img string `json:"base64Img"`
}

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool {
		return true
	},
}

func handleWebSocket(w http.ResponseWriter, r *http.Request) {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		fmt.Println("웹소켓 업그레이드 실패:", err)
		return
	}
	defer conn.Close()

	for {
		_, message, err := conn.ReadMessage()
		if err != nil {
			fmt.Println("메시지 읽기 실패:", err)
			break
		}

		var imgData ImageData
		err = json.Unmarshal(message, &imgData)
		if err != nil {
			fmt.Println("JSON 디코딩 실패", err)
			continue
		}

		switch imgData.Command {
		case "upload":
			if strings.HasPrefix(imgData.Base64Img, "data:image/") {
				imageDataIndex := strings.Index(imgData.Base64Img, ",") + 1
				if imageDataIndex <= 0 {
					fmt.Println("올바른 base64 데이터 형식을 찾을 수 없습니다.")
					continue
				}

				imageData := imgData.Base64Img[imageDataIndex:]
				imgBytes, err := base64.StdEncoding.DecodeString(imageData)
				if err != nil {
					fmt.Println("base64 디코딩 실패:", err)
					continue
				}

				fileName := imgData.ID + ".jpg"
				file, err := os.Create("images/" + fileName)
				if err != nil {
					fmt.Println("이미지 파일 생성 실패:", err)
					continue
				}
				defer file.Close()

				_, err = file.Write(imgBytes)
				if err != nil {
					fmt.Println("이미지 파일 저장 실패:", err)
					continue
				}

				fmt.Println("이미지 저장 성공:", fileName)
			}

		case "request":
			if imgData.ID != "" {
				fileName := "images/" + imgData.ID + ".jpg"
				if _, err := os.Stat(fileName); os.IsNotExist(err) {
					fmt.Println("이미지 파일을 찾을 수 없습니다:", fileName)
					continue
				}

				file, err := os.Open(fileName)
				if err != nil {
					fmt.Println("이미지 파일 열기 실패:", err)
					continue
				}
				defer file.Close()

				imgBytes := make([]byte, 0)
				stat, _ := file.Stat()
				imgBytes = make([]byte, stat.Size())
				_, err = file.Read(imgBytes)
				if err != nil {
					fmt.Println("이미지 파일 읽기 실패:", err)
					continue
				}

				encodedImage := base64.StdEncoding.EncodeToString(imgBytes)
				responseData := "data:image/jpg;base64," + encodedImage

				err = conn.WriteMessage(websocket.TextMessage, []byte(responseData))
				if err != nil {
					fmt.Println("메시지 전송 실패:", err)
					break
				}

				fmt.Println("이미지 전송 성공:", fileName)
			}

		default:
			fmt.Println("알 수 없는 명령어:", imgData.Command)
		}
	}
}
func main() {
	http.HandleFunc("/ws", handleWebSocket)

	fmt.Println("서버가 8000 포트에서 실행 중입니다...")
	if err := http.ListenAndServe("0.0.0.0:8000", nil); err != nil {
		fmt.Println("서버 실행 실패:", err)
	}
}
