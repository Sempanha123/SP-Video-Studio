import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

AppDialog {
    id: root
    property var resultData: ({})
    signal copyRequested(string value)
    width: Math.min(720, parent ? parent.width - 48 : 720)
    height: Math.min(620, parent ? parent.height - 48 : 620)
    header: null
    footer: null
    contentItem: ColumnLayout {
        spacing: Theme.spacing.md
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                Text { text: root.resultData.name || "Diagnostic details"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.title; font.weight: Theme.type.semibold }
                Text { text: root.resultData.category || ""; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            }
            StatusBadge { text: String(root.resultData.status || "checking").replaceAll("_", " "); status: root.resultData.status || "checking" }
        }
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            ColumnLayout {
                width: parent.width
                spacing: Theme.spacing.md
                Text { Layout.fillWidth: true; text: root.resultData.summary || ""; wrapMode: Text.WordWrap; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodyStrong }
                Text { Layout.fillWidth: true; text: root.resultData.details || ""; wrapMode: Text.WrapAnywhere; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
                InfoBanner { Layout.fillWidth: true; visible: !!root.resultData.recommendation; text: root.resultData.recommendation || "" }
                ColumnLayout {
                    Layout.fillWidth: true
                    visible: !!root.resultData.technicalDetails
                    Text { text: "Technical Details"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.label; font.weight: Theme.type.semibold }
                    TextArea {
                        Layout.fillWidth: true
                        readOnly: true
                        wrapMode: TextEdit.WrapAnywhere
                        text: root.resultData.technicalDetails || ""
                        color: Theme.colors.textSecondary
                        font.family: Theme.type.family
                        font.pixelSize: Theme.type.caption
                        background: Rectangle { radius: Theme.radius.medium; color: Theme.colors.surfaceHover; border.color: Theme.colors.border }
                    }
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            SecondaryButton { visible: !!root.resultData.technicalDetails; text: "Copy Technical Details"; onClicked: root.copyRequested(root.resultData.technicalDetails || "") }
            Item { Layout.fillWidth: true }
            AppButton { text: "Close"; onClicked: root.close() }
        }
    }
}
