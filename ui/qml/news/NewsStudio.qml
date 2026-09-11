import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

Item {
    id:root
    property var controller
    property string currentTab:"overview"
    signal navigateRequested(string mode)
    signal toastRequested(string message,string variant)

    Connections { target:root.controller; ignoreUnknownSignals:true; function onOperationFailed(message){root.toastRequested(message,"error")} function onOperationSucceeded(message){root.toastRequested(message,"success")} function onNavigationRequested(mode){root.navigateRequested(mode)} }
    ColumnLayout { anchors.fill:parent; spacing:Theme.spacing.md
        RowLayout { Layout.fillWidth:true
            ColumnLayout { Layout.fillWidth:true; Text { text:"News Studio"; color:Theme.colors.textPrimary; font.pixelSize:Theme.type.titleLarge; font.weight:Theme.type.semibold }; Text { text:"Sources → Facts → Brief → Script → Video"; color:Theme.colors.textMuted; font.pixelSize:Theme.type.caption } }
            Repeater { model:["overview","sources","claims","brief","script"]; AppButton { text:modelData.charAt(0).toUpperCase()+modelData.slice(1); compact:true; variant:root.currentTab===modelData?"secondary":"ghost"; onClicked:root.currentTab=modelData } }
        }
        NewsSetup { Layout.fillWidth:true; visible:root.currentTab==="overview"; controller:root.controller }
        NewsReadiness { Layout.fillWidth:true; Layout.fillHeight:true; visible:root.currentTab==="overview"; overview:root.controller?root.controller.overview:({}) }
        NewsSources { Layout.fillWidth:true; Layout.fillHeight:true; visible:root.currentTab==="sources"; controller:root.controller; onToastRequested:root.toastRequested(message,variant) }
        NewsClaims { Layout.fillWidth:true; Layout.fillHeight:true; visible:root.currentTab==="claims"; controller:root.controller }
        NewsBrief { Layout.fillWidth:true; Layout.fillHeight:true; visible:root.currentTab==="brief"; controller:root.controller }
        NewsScriptBuilder { Layout.fillWidth:true; Layout.fillHeight:true; visible:root.currentTab==="script"; controller:root.controller; onNavigateRequested:root.navigateRequested(mode) }
        RowLayout { Layout.fillWidth:true; visible:root.currentTab==="overview"; SecondaryButton { text:"Sources"; onClicked:root.currentTab="sources" }; SecondaryButton { text:"Script"; onClicked:root.navigateRequested("script") }; SecondaryButton { text:"Scenes"; onClicked:root.navigateRequested("scenes") }; SecondaryButton { text:"Subtitles"; onClicked:root.navigateRequested("subtitles") }; SecondaryButton { text:"Timeline"; onClicked:root.navigateRequested("timeline") }; SecondaryButton { text:"Export"; onClicked:root.navigateRequested("export") }; Item { Layout.fillWidth:true } }
    }
}
