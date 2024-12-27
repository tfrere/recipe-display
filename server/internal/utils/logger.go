package utils

import (
	"fmt"
	"log"
	"os"
	"runtime"
	"strings"
)

type LogLevel int

const (
	DEBUG LogLevel = iota
	INFO
	WARN
	ERROR
)

var currentLogLevel LogLevel = INFO

func init() {
	// Configurer le niveau de log depuis l'environnement
	logLevelStr := os.Getenv("LOG_LEVEL")
	switch strings.ToUpper(logLevelStr) {
	case "DEBUG":
		currentLogLevel = DEBUG
	case "INFO":
		currentLogLevel = INFO
	case "WARN":
		currentLogLevel = WARN
	case "ERROR":
		currentLogLevel = ERROR
	default:
		currentLogLevel = INFO
	}
}

func SetLogLevel(level LogLevel) {
	currentLogLevel = level
}

func getCallerInfo() string {
	_, file, line, ok := runtime.Caller(2)
	if !ok {
		return ""
	}
	// Extraire uniquement le nom du fichier et le numéro de ligne
	parts := strings.Split(file, "/")
	return fmt.Sprintf("%s:%d", parts[len(parts)-1], line)
}

func Debug(format string, v ...interface{}) {
	if currentLogLevel <= DEBUG {
		log.Printf("[DEBUG] %s: %s", getCallerInfo(), fmt.Sprintf(format, v...))
	}
}

func Info(format string, v ...interface{}) {
	if currentLogLevel <= INFO {
		log.Printf("[INFO] %s: %s", getCallerInfo(), fmt.Sprintf(format, v...))
	}
}

func Warn(format string, v ...interface{}) {
	if currentLogLevel <= WARN {
		log.Printf("[WARN] %s: %s", getCallerInfo(), fmt.Sprintf(format, v...))
	}
}

func Error(format string, v ...interface{}) {
	if currentLogLevel <= ERROR {
		log.Printf("[ERROR] %s: %s", getCallerInfo(), fmt.Sprintf(format, v...))
	}
}

func Fatal(format string, v ...interface{}) {
	log.Fatalf("[FATAL] %s: %s", getCallerInfo(), fmt.Sprintf(format, v...))
}

func FatalError(err error) {
	log.Fatalf("[FATAL] %s: %v", getCallerInfo(), err)
}
