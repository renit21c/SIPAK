import React from 'react';
import {createRoot} from 'react-dom/client';
import App from './App';
import {WebIntro} from './WebIntro';
import './styles.css';
import './motion.css';
import './login.css';
import './komdis.css';
import './scrollbars.css';
import './findings.css';
import './evaluation.css';
import './ui-focus.css';
import './responsive.css';
import './workspace-theme.css';
createRoot(document.getElementById('root')!).render(<React.StrictMode><WebIntro><App/></WebIntro></React.StrictMode>);

if(import.meta.env.PROD&&'serviceWorker' in navigator){
 window.addEventListener('load',()=>{navigator.serviceWorker.register('/sw.js').catch(()=>{})});
}
