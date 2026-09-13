import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtMultimedia
import SPVideoStudio.Commands 1.0
import "../theme"
import "../components"

AppDialog {
    id: root
    width: 720
    height: 520
    header: null
    footer: null
    property var asset: ({})
    function localUrl(path) {
        var value=String(path||"").replaceAll("\\\\","/")
        return value.length ? "file:///"+value : ""
    }
    function showAsset(item) { asset=item||({}); open() }
    onOpened: {
        Commands.setModalOpen(true)
        if ((asset.type||"")==="video" || (asset.type||"")==="audio") {
            player.source=localUrl(asset.resolvedPath||"")
            player.play()
        }
    }
    onClosed: { player.stop(); player.source=""; Commands.setModalOpen(false) }

    MediaPlayer { id: player; audioOutput: AudioOutput {} ; videoOutput: videoOut }
    contentItem: ColumnLayout {
        spacing: Theme.spacing.md
        RowLayout {
            Layout.fillWidth: true
            Text { Layout.fillWidth:true; text:asset.name||"Asset Preview"; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.heading; font.weight:Theme.type.semibold; elide:Text.ElideRight }
            SecondaryButton { text:"Close"; onClicked:root.close() }
        }
        Rectangle {
            Layout.fillWidth:true; Layout.fillHeight:true; radius:Theme.radius.medium; color:Theme.colors.previewBackground; border.color:Theme.colors.borderStrong; clip:true
            Image { anchors.fill:parent; anchors.margins:Theme.spacing.md; source:(asset.type||"")==="image"?root.localUrl(asset.resolvedPath||""):""; fillMode:Image.PreserveAspectFit; visible:(asset.type||"")==="image" }
            VideoOutput { id:videoOut; anchors.fill:parent; visible:(asset.type||"")==="video"; fillMode:VideoOutput.PreserveAspectFit }
            Column { anchors.centerIn:parent; spacing:Theme.spacing.sm; visible:(asset.type||"")==="audio"
                Text { anchors.horizontalCenter:parent.horizontalCenter; text:"♪"; color:Theme.colors.accent; font.pixelSize:48 }
                Text { anchors.horizontalCenter:parent.horizontalCenter; text:"Audio preview"; color:Theme.colors.textSecondary; font.family:Theme.type.family; font.pixelSize:Theme.type.body }
            }
        }
        RowLayout {
            Layout.fillWidth:true
            SecondaryButton { text:player.playbackState===MediaPlayer.PlayingState?"Pause":"Play"; visible:(asset.type||"")==="video"||(asset.type||"")==="audio"; onClicked:player.playbackState===MediaPlayer.PlayingState?player.pause():player.play() }
            Item { Layout.fillWidth:true }
            Text { text:(asset.type||"").toUpperCase(); color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
        }
    }
}
