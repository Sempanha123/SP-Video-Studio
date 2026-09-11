import QtQuick 2.15
import SPVideoStudio.Phase25 1.0
import "../assets"
Item {
    id:root
    signal navigateRequested(string page,string workflow)
    signal toastRequested(string message,string variant)
    AssetLibraryPage { anchors.fill:parent; onToastRequested:function(message,variant){root.toastRequested(message,variant)} }
    Component.onCompleted: AssetLibrary.setCurrentProject(typeof projectController!=="undefined" ? (projectController.currentProject.id||"") : "")
    Connections { target:typeof projectController!=="undefined"?projectController:null; ignoreUnknownSignals:true; function onCurrentProjectChanged(){AssetLibrary.setCurrentProject(projectController.currentProject.id||"")} }
}
