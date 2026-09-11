import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import "../theme"
import "../components"

Item {
    id: root
    property var controller
    signal toastRequested(string message, string variant)
    RowLayout { anchors.fill: parent; spacing: Theme.spacing.md
        AppCard { Layout.preferredWidth: 420; Layout.fillHeight: true
            ColumnLayout { anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.md
                RowLayout { Layout.fillWidth: true; Text { Layout.fillWidth: true; text: "Sources"; color: Theme.colors.textPrimary; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }; AppButton { text: "Add Web"; compact: true; onClicked: webDialog.open() }; SecondaryButton { text: "Paste"; compact: true; onClicked: manualDialog.open() }; SecondaryButton { text: "Local"; compact: true; onClicked: fileDialog.open() }; SecondaryButton { text: "Refresh All"; compact: true; enabled: root.controller && !root.controller.busy; onClicked: root.controller.refreshAllSources() } }
                ScrollView { Layout.fillWidth: true; Layout.fillHeight: true
                    Column { width: parent.width; spacing: Theme.spacing.sm
                        Repeater { model: root.controller ? root.controller.sources : []
                            NewsSourceCard { width: parent.width; source: modelData; selected: root.controller && (root.controller.currentSource.id||"") === (modelData.id||""); onSelectedRequested: root.controller.selectSource(id); onRefreshRequested: root.controller.refreshSource(id); onRemoveRequested: root.controller.removeSource(id) }
                        }
                    }
                }
                AppButton { Layout.fillWidth: true; text: root.controller && root.controller.busy ? "Working…" : "Extract Candidate Claims"; enabled: root.controller && !root.controller.busy && (root.controller.currentSource.id||"")!==""; onClicked: root.controller.extractClaims(root.controller.currentSource.id) }
            }
        }
        NewsSourceInspector { Layout.fillWidth: true; Layout.fillHeight: true; controller: root.controller; source: root.controller ? root.controller.currentSource : ({}); snapshot: root.controller ? root.controller.currentSnapshot : ({}) }
    }
    AppDialog { id:webDialog; width:520; parent:Overlay.overlay; contentItem: ColumnLayout { spacing:Theme.spacing.md; Text { text:"Add public web source"; color:Theme.colors.textPrimary; font.pixelSize:Theme.type.heading }; AppTextField { id:webUrl; Layout.fillWidth:true; placeholderText:"https://example.com/article" }; InfoBanner { Layout.fillWidth:true; variant:"info"; text:"Only the URL you enter and its validated public redirects are fetched. Private/internal network targets are blocked." }; RowLayout { Layout.fillWidth:true; Item { Layout.fillWidth:true }; SecondaryButton { text:"Cancel"; onClicked:webDialog.close() }; AppButton { text:"Fetch Source"; onClicked:{ if(root.controller.addUrlSource(webUrl.text,"","auto","reporting")){webDialog.close();webUrl.text=""} } } } } }
    AppDialog { id:manualDialog; width:620; parent:Overlay.overlay; contentItem: ColumnLayout { spacing:Theme.spacing.md; Text { text:"Paste source text"; color:Theme.colors.textPrimary; font.pixelSize:Theme.type.heading }; AppTextField { id:manualTitle; Layout.fillWidth:true; placeholderText:"Source name" }; TextArea { id:manualText; Layout.fillWidth:true; Layout.preferredHeight:260; wrapMode:TextArea.Wrap; placeholderText:"Paste authorized source text or notes…" }; RowLayout { Layout.fillWidth:true; Item { Layout.fillWidth:true }; SecondaryButton { text:"Cancel"; onClicked:manualDialog.close() }; AppButton { text:"Add Source"; onClicked:{ if(root.controller.addManualSource(manualTitle.text,manualText.text,"","","auto","manual_note")){manualDialog.close();manualTitle.text="";manualText.text=""} } } } } }
    FileDialog { id:fileDialog; title:"Add local text source"; fileMode:FileDialog.OpenFile; nameFilters:["Text Sources (*.txt *.md *.html *.htm)"]; onAccepted: root.controller.addLocalSource(selectedFile,"","auto","primary_document") }
}
