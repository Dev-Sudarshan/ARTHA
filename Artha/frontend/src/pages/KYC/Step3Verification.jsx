import { useEffect, useRef, useState } from 'react';
import Webcam from 'react-webcam';
import { RefreshCw, Camera } from 'lucide-react';

const Step3Verification = ({ data, updateData, submit, prevStep, loading }) => {
    const webcamRef = useRef(null);
    const [recordedVideo, setRecordedVideo] = useState(data.liveVideoUrl || null);
    const [recording, setRecording] = useState(false);

    useEffect(() => {
        return () => {
            if (recordedVideo && recordedVideo.startsWith('blob:')) {
                URL.revokeObjectURL(recordedVideo);
            }
        };
    }, [recordedVideo]);

    const recordVideo = () => {
        if (!webcamRef.current?.video?.srcObject) {
            alert('Camera not ready');
            return;
        }
        const chunks = [];
        const recorder = new MediaRecorder(webcamRef.current.video.srcObject, { mimeType: 'video/webm' });
        recorder.ondataavailable = (event) => event.data.size && chunks.push(event.data);
        recorder.onstop = () => {
            const blob = new Blob(chunks, { type: 'video/webm' });
            const file = new File([blob], 'live-verification.webm', { type: 'video/webm' });
            const url = URL.createObjectURL(blob);
            setRecordedVideo(url);
            updateData('liveVideo', file);
            updateData('liveVideoUrl', url);
            setRecording(false);
        };
        recorder.start();
        setRecording(true);
        window.setTimeout(() => recorder.state === 'recording' && recorder.stop(), 3000);
    };

    const retake = () => {
        if (recordedVideo && recordedVideo.startsWith('blob:')) {
            URL.revokeObjectURL(recordedVideo);
        }
        setRecordedVideo(null);
        updateData('liveVideo', null);
        updateData('liveVideoUrl', null);
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!recordedVideo) {
            alert("Please record the live video first");
            return;
        }
        submit();
    };

    return (
        <div className="text-center">
            <h3 className="form-section-title">Live Video</h3>
            <p className="mb-2 text-muted">Record a clear 2-3 second live video for admin review.</p>
            <p className="mb-4 text-muted">Keep your face centered and stay within arm's length.</p>

            <div className="camera-section mb-4">
                {recordedVideo ? (
                    <div>
                        <video src={recordedVideo} controls className="captured-image" />
                        <div className="mt-4">
                            <button type="button" onClick={retake} className="btn btn-outline">
                                <RefreshCw size={18} className="mr-2" style={{ marginRight: '0.5rem' }} /> Retake
                            </button>
                        </div>
                    </div>
                ) : (
                    <div className="webcam-wrapper">
                        <div className="webcam-container">
                            <Webcam
                                audio={false}
                                ref={webcamRef}
                                width="100%"
                                screenshotFormat="image/jpeg"
                            />
                        </div>
                        <div className="mt-4">
                            <button type="button" onClick={recordVideo} className="btn btn-primary" disabled={recording}>
                                <Camera size={18} className="mr-2" style={{ marginRight: '0.5rem' }} />
                                {recording ? 'Recording...' : 'Record 3-Second Video'}
                            </button>
                        </div>
                    </div>
                )}
            </div>

            <div className="flex justify-between mt-8">
                <button type="button" onClick={prevStep} className="btn btn-outline" disabled={loading}>Back</button>
                    <button type="button" onClick={handleSubmit} className="btn btn-primary btn-lg" disabled={!recordedVideo || recording || loading}>
                    {loading ? 'Submitting...' : 'Submit Verification'}
                </button>
            </div>
        </div>
    );
};

export default Step3Verification;
