import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"

AppCard {
    id: root
    property string title: ""
    property string description: ""
    default property alias contentData: body.data
    implicitHeight: body.implicitHeight + Theme.spacing.xl * 2

    ColumnLayout {
        id: body
        anchors.fill: parent
        anchors.margins: Theme.spacing.xl
        spacing: Theme.spacing.lg

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.spacing.xs
            Text {
                text: root.title
                color: Theme.colors.textPrimary
                font.family: Theme.type.family
                font.pixelSize: Theme.type.heading
                font.weight: Theme.type.semibold
            }
            Text {
                visible: root.description.length > 0
                text: root.description
                color: Theme.colors.textSecondary
                font.family: Theme.type.family
                font.pixelSize: Theme.type.bodySmall
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
        }
    }
}
