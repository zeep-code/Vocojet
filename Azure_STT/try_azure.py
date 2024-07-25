import os 
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk

# {0.0.1.00000000}.{0B58E07B-C614-4621-89D2-F1FBC4616E95}

'''Takes api_key and region as arguments
inside the function: 
create an object speech-config which is going to be our connection to the api
then we set the speech recognition language to english
then we create another object audio-config to configure our audio input device using speechsdk.audio.audioconfig

then we create a speech-recognizer object to which we will provide
the speech-configuration setting from the speech config object and the audio setting from the audio-config object'''


def speak_to_microphone(api_key, region):

    # Debugging prints
    print(f"API Key: {api_key}")
    print(f"Region: {region}")

        # Ensure api_key and region are not None or empty
    if not api_key or not region:
        raise ValueError("API Key and region must be provided")



    speech_config = speechsdk.SpeechConfig(subscription=api_key, region=region)
    speech_config.speech_recognition_language = "en-US"
    audio_config = speechsdk.audio.AudioConfig(device_name='{0.0.1.00000000}.{0B58E07B-C614-4621-89D2-F1FBC4616E95}')
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
    
    # Setting timeout durations using speech_recognizer.properties
    speech_recognizer.properties.set_property(speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, "60000") # 60 seconds
    speech_recognizer.properties.set_property(speechsdk.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, "20000") # 20 seconds
    
    print("Speak into your microphone. Say 'stop session' to end.")
    
    # stream audio to text using a while loop
    while True:
        speech_recognition_result = speech_recognizer.recognize_once_async().get() # this function is going to wait any audio signals
        
        if speech_recognition_result.reason == speechsdk.ResultReason.RecognizedSpeech: # if any apeech is detected
            print("Recognized: {}".format(speech_recognition_result.text)) # print Recognized: and the text from speech audio
            if "stop session" in speech_recognition_result.text.lower(): # if speech contains text "stop session" program terminates
                print("Session ended by user.")
                break
        # if no "stop session" then check for other condition using NoMatch i.e. if audio/speech is not a valid audio/speech
        elif speech_recognition_result.reason == speechsdk.ResultReason.NoMatch:
            print("No speech could be recognized: {}".format(speech_recognition_result.no_match_details))
            
        # can be used with our own speicifc operation to cancel the operation/method to trigger this condition    
        elif speech_recognition_result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = speech_recognition_result.cancellation_details
            print("Speech Recognition canceled: {}".format(cancellation_details.reason))
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                print("Error details: {}".format(cancellation_details.error_details))
                print("Did you set the speech resource key and region values?")

# Load the api key and region
load_dotenv()
api_key = os.getenv("api_key")
region = os.getenv("region")

# Debugging prints
print(f"API Key: {api_key}")
print(f"Region: {region}")

speak_to_microphone(api_key, region)

    
